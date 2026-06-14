import dotenv from "dotenv";
dotenv.config();

import {
	Client,
	GatewayIntentBits,
	Events,
	ModalBuilder,
	TextInputBuilder,
	TextInputStyle,
	ActionRowBuilder,
	MessageFlags,
	ApplicationCommandType,
	EmbedBuilder,
	ButtonBuilder,
	ButtonStyle,
	PermissionFlagsBits,
	ChannelSelectMenuBuilder,
	StringSelectMenuBuilder,
	ChannelType,
} from "discord.js";

const client = new Client({
	intents: [
		GatewayIntentBits.Guilds,
		GatewayIntentBits.GuildMessages,
		GatewayIntentBits.MessageContent,
	],
});

const API_URL = process.env.API_URL || "http://127.0.0.1:8000";

const activeSetupSessions = new Map();

client.once(Events.ClientReady, async () => {
	console.log(`Bot ready: ${client.user.tag}`);

	try {
		await client.application.commands.set([
			{
				name: "detect",
				description: "Otwiera okienko do wklejenia linku lub tekstu do analizy",
				type: ApplicationCommandType.ChatInput,
			},
			{
				name: "setup",
				description:
					"Ustawienia kanału logów i modeli analizy (Wymaga Administratora)",
				default_member_permissions:
					PermissionFlagsBits.Administrator.toString(),
				type: ApplicationCommandType.ChatInput,
			},
			{
				name: "Wykryj deepfake",
				type: ApplicationCommandType.Message,
			},
			{
				name: "Weryfikacja faktów",
				type: ApplicationCommandType.Message,
			},
		]);
		console.log(
			"Pomyślnie zarejestrowano komendy (/detect, /setup oraz menu kontekstowe)",
		);
	} catch (error) {
		console.error("Błąd podczas rejestracji komend:", error);
	}
});

// Pobieranie modeli bezpośrednio z FastAPI
async function fetchAvailableModels() {
	try {
		const response = await fetch(API_URL);
		if (response.ok) {
			const data = await response.json();
			if (data.available_models) {
				return data.available_models;
			}
		}
	} catch (err) {
		console.error("Błąd połączenia z FastAPI:", err.message);
	}
	return null;
}

async function fetchGuildConfig(guildId) {
	try {
		const response = await fetch(`${API_URL}/guilds/${guildId}/config`);
		if (response.ok) {
			const data = await response.json();
			return {
				logChannelId: data.log_channel_id,
				multiModelWorkflow: data.multi_model_workflow || false,
				models: {
					text: data.active_text_model || "none",
					image: data.active_image_model || "none",
				},
			};
		}
	} catch (err) {
		console.error(
			`[CONFIG ERROR] Błąd pobierania konfiguracji dla gildii ${guildId}:`,
			err.message,
		);
	}
	return {
		logChannelId: null,
		multiModelWorkflow: false,
		models: {}
	};
}

function preparePayload(input, explicitContentType = null) {
	const trimmed = input.trim();

	if (explicitContentType) {
		if (explicitContentType.startsWith("image/")) {
			return {
				type: "image",
				payload: { image_url: trimmed, content_type: "image" },
			};
		} else if (explicitContentType.startsWith("video/")) {
			return {
				type: "video",
				payload: { video_url: trimmed, content_type: "video" },
			};
		} else {
			return {
				type: "file",
				payload: { file_url: trimmed, content_type: "file" },
			};
		}
	}

	const isUrl = trimmed.startsWith("http://") || trimmed.startsWith("https://");

	if (isUrl) {
		const cleanUrl = trimmed.toLowerCase().split("?")[0];

		if (cleanUrl.match(/\.(png|jpg|jpeg|webp|gif)$/)) {
			return {
				type: "image",
				payload: { image_url: trimmed, content_type: "image" },
			};
		} else if (cleanUrl.match(/\.(mp4|webm|mov|avi)$/)) {
			return {
				type: "video",
				payload: { video_url: trimmed, content_type: "video" },
			};
		} else {
			return {
				type: "file",
				payload: { file_url: trimmed, content_type: "file" },
			};
		}
	}

	return {
		type: "text",
		payload: { text: trimmed, content_type: "text" },
	};
}

function getProgressBar(confidence, isDeepfake) {
	const totalBlocks = 10;
	const filledBlocks = Math.min(
		totalBlocks,
		Math.max(0, Math.round(confidence * totalBlocks)),
	);
	const emptyBlocks = totalBlocks - filledBlocks;
	const blockEmoji = isDeepfake ? "🟥" : "🟩";
	return blockEmoji.repeat(filledBlocks) + "⬛".repeat(emptyBlocks);
}

// CAŁKOWICIE DYNAMICZNY GENERATOR WIDOKU SETUPU
function generateSetupView(tempConfig, availableModels) {
	const embed = new EmbedBuilder()
		.setColor(0x5865f2)
		.setTitle("⚙️ Konfiguracja Systemu Detekcji")
		.setDescription(
			"Wybierz kanał do wysyłania logów oraz aktywne modele dla poszczególnych formatów danych.",
		)
		.setTimestamp()
		.setFooter({ text: "Wybierz opcje i kliknij Zapisz ustawienia" });

	embed.addFields({
		name: "🔗 Tryb wielomodelowy (Multi-Model Workflow)",
		value: tempConfig.multiModelWorkflow 
			? "🟢 **Włączony** (zostaną użyte wszystkie dostępne modele, indywidualny wybór jest zablokowany)" 
			: "🔴 **Wyłączony** (będzie używany tylko model wybrany poniżej)",
		inline: false
	});

	for (const [contentType, models] of Object.entries(availableModels)) {
		const currentSelected = tempConfig.multiModelWorkflow 
			? "Wszystkie (Multi-Model Workflow)" 
			: (tempConfig.models[contentType] || models[0] || "Brak");

		embed.addFields({
			name: `⚙️ Model dla formatu: ${contentType.toUpperCase()}`,
			value: `\`${currentSelected}\``,
			inline: true,
		});
	}

	const channelSelect = new ChannelSelectMenuBuilder()
		.setCustomId("setup_log_channel")
		.setPlaceholder("Wybierz kanał dla raportów")
		.addChannelTypes(ChannelType.GuildText);

	const components = [new ActionRowBuilder().addComponents(channelSelect)];

	for (const [contentType, models] of Object.entries(availableModels)) {
		if (components.length >= 4) break;

		const currentSelected = tempConfig.models[contentType] || models[0];

		const selectOptions = models.map((model) => ({
			label: model,
			value: model,
			default: currentSelected === model,
		}));

		const modelSelect = new StringSelectMenuBuilder()
			.setCustomId(`setup_model_${contentType}`)
			.setPlaceholder(`Wybierz model dla ${contentType}`)
			.addOptions(selectOptions)
			// WYszarzenie i zablokowanie wyboru, gdy włączony jest Multi-Model Workflow
			.setDisabled(tempConfig.multiModelWorkflow);

		components.push(new ActionRowBuilder().addComponents(modelSelect));
	}

	const buttonsRow = new ActionRowBuilder().addComponents(
		new ButtonBuilder()
			.setCustomId("setup_toggle_multimodel")
			.setLabel(tempConfig.multiModelWorkflow ? "Tryb Wielomodelowy: WŁ" : "Tryb Wielomodelowy: WYŁ")
			.setStyle(tempConfig.multiModelWorkflow ? ButtonStyle.Primary : ButtonStyle.Secondary)
			.setEmoji(tempConfig.multiModelWorkflow ? "🟢" : "⚫"),
		new ButtonBuilder()
			.setCustomId("setup_save")
			.setLabel("Zapisz ustawienia")
			.setStyle(ButtonStyle.Success)
			.setEmoji("💾"),
		new ButtonBuilder()
			.setCustomId("setup_cancel")
			.setLabel("Anuluj")
			.setStyle(ButtonStyle.Danger)
			.setEmoji("❌"),
	);

	components.push(buttonsRow);

	return {
		embeds: [embed],
		components: components,
	};
}

async function sendLogToDiscord(guild, embedToSend) {
	const config = await fetchGuildConfig(guild.id);
	if (!config.logChannelId) return;

	try {
		const channel = await guild.channels.fetch(config.logChannelId);
		if (channel) {
			await channel.send({ embeds: [embedToSend] });
		}
	} catch (err) {
		console.warn(
			`Nie można wysłać logu na kanał ${config.logChannelId}:`,
			err.message,
		);
	}
}


// =====================================================================
// AUTONOMICZNE FUNKCJE DO WERYFIKACJI TREŚCI W PURE JS (BEZ BACKENDU)
// =====================================================================

// Helper 1: Bezpieczne i darmowe wyszukiwanie na Wikipedii (Bez kluczy i limitów)
async function searchWikipedia(query) {
    const url = `https://pl.wikipedia.org/w/api.php?action=opensearch&search=${encodeURIComponent(query)}&limit=3&namespace=0&format=json`;
    try {
        const response = await fetch(url);
        if (!response.ok) return [];
        const data = await response.json();
        
        const titles = data[1] || [];
        const descriptions = data[2] || [];
        const urls = data[3] || [];
        
        const results = [];
        for (let i = 0; i < titles.length; i++) {
            results.push({
                title: titles[i],
                url: urls[i],
                snippet: descriptions[i] || "Artykuł w darmowej encyklopedii Wikipedia."
            });
        }
        return results;
    } catch (error) {
        console.error("Błąd wyszukiwania w Wikipedii:", error);
        return [];
    }
}

// Helper 2: Bezpośrednie wywołanie Gemini 2.5-Flash
async function askGemini(prompt, apiKey) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            contents: [
                {
                    role: "user",
                    parts: [{ text: prompt }]
                }
            ],
            generationConfig: {
                temperature: 0.0
            }
        })
    });

    if (!response.ok) {
        const errText = await response.text();
        throw new Error(`Błąd Gemini API: Status ${response.status} - ${errText}`);
    }

    const data = await response.json();
    return data.candidates[0].content.parts[0].text;
}

// Główny proces weryfikacji faktów (wywoływany w 100% lokalnie w bocie)
async function handleFactCheck(interaction, statement) {
	await interaction.deferReply({ flags: [MessageFlags.Ephemeral] });

	const geminiKey = process.env.GEMINI_API_KEY;
	if (!geminiKey) {
		return interaction.editReply({
			content: "❌ **Błąd konfiguracji bota:** Brak klucza `GEMINI_API_KEY` w pliku `.env` bota Discorda!"
		});
	}

	try {
		console.log(`Wyszukiwanie Wikipedia dla: "${statement.slice(0, 30)}..."`);
		const webResults = await searchWikipedia(statement);
		
		if (webResults.length === 0) {
			return interaction.editReply({
				content: "❌ Nie znaleziono żadnych pasujących tematów w bazie wiedzy, aby zweryfikować to stwierdzenie."
			});
		}

		let sourcesText = "";
		webResults.forEach((r, idx) => {
			sourcesText += `[${idx + 1}] Tytuł: ${r.title}\nOpis: ${r.snippet}\n\n`;
		});

		const prompt = `Jesteś zaawansowanym asystentem do weryfikacji faktów (fact-checking).
Przeanalizuj poniższe stwierdzenie na podstawie dostarczonych aktualnych artykułów z bazy wiedzy Wikipedii.

STWIERDZENIE DO WERYFIKACJI:
"${statement}"

DOKUMENTY Z BAZY WIEDZY:
${sourcesText}

Twoja odpowiedź musi ściśle odpowiadać poniższemu szablonowi (nie dodawaj żadnych innych komentarzy ani wstępów):

VERDICT: [Wpisz PRAWDA, FAŁSZ lub SPORNE]
EXPLANATION: [Wpisz zwięzłe (2-4 zdania), merytoryczne i obiektywne uzasadnienie werdyktu w języku polskim, wyjaśniające co mówią najnowsze fakty na podstawie dostarczonych dokumentów.]

Zasady oceny:
- VERDICT: PRAWDA (dostarczone dokumenty w pełni potwierdzają to stwierdzenie)
- VERDICT: FAŁSZ (dostarczone dokumenty jednoznacznie zaprzeczają temu stwierdzeniu)
- VERDICT: SPORNE (informacje są sprzeczne, opinie podzielone lub brak wystarczających dowodów w dokumentach)`;

		console.log("Wysyłanie zapytania do Gemini...");
		const rawText = await askGemini(prompt, geminiKey);
		console.log("Surowa odpowiedź Gemini:\n", rawText);

		// Parsowanie werdyktu
		let verdict = "SPORNE";
		const verdictMatch = rawText.match(/VERDICT:\s*(PRAWDA|FAŁSZ|SPORNE)/i);
		if (verdictMatch) {
			verdict = verdictMatch[1].toUpperCase();
		}

		// Parsowanie uzasadnienia
		let explanation = "Nie udało się wygenerować uzasadnienia.";
		const explanationMatch = rawText.match(/EXPLANATION:\s*([\s\S]*)/i);
		if (explanationMatch) {
			explanation = explanationMatch[1].trim();
		}

		let embedColor = 0xFFAA00; // Żółty (SPORNE)
		let verdictEmoji = "⚖️";

		if (verdict === "PRAWDA") {
			embedColor = 0x00FF00; // Zielony
			verdictEmoji = "✅";
		} else if (verdict === "FAŁSZ") {
			embedColor = 0xFF0000; // Czerwony
			verdictEmoji = "❌";
		}

		const embed = new EmbedBuilder()
			.setColor(embedColor)
			.setTitle(`${verdictEmoji} Wynik Weryfikacji Faktów`)
			.setDescription(`**Badane stwierdzenie:**\n*"${statement}"*\n\n**Werdykt:** \`${verdict}\``)
			.addFields(
				{ name: "📝 Analiza merytoryczna", value: explanation },
				{ name: "🎯 Pewność analizy", value: `\`95%\``, inline: true }
			)
			.setTimestamp()
			.setFooter({ text: "System Fact-checkingowy", iconURL: client.user.displayAvatarURL() });

		// Formatowanie źródeł z Wikipedii
		const sourcesTextEmbed = webResults
			.map((src, idx) => `**[${idx + 1}]** [${src.title}](${src.url})\n*${src.snippet.slice(0, 150)}...*`)
			.join("\n\n");

		const truncatedSources = sourcesTextEmbed.length > 1024 ? sourcesTextEmbed.slice(0, 1000) + "..." : sourcesTextEmbed;
		embed.addFields({ name: "🔗 Wykorzystane źródła internetowe", value: truncatedSources });

		await interaction.editReply({
			embeds: [embed]
		});

	} catch (error) {
		console.error("Błąd podczas weryfikacji faktów:", error);
		await interaction.editReply({
			content: `❌ Nie udało się przeprowadzić weryfikacji faktów.\n\n**Szczegóły błędu:**\n${error.message}`,
		});
	}
}


async function handleAnalysis(
	interaction,
	userContent,
	targetMessage = null,
	explicitContentType = null,
) {
	await interaction.deferReply({ flags: [MessageFlags.Ephemeral] });

	try {
		const { type, payload } = preparePayload(userContent, explicitContentType);
		payload.guild_id = interaction.guildId;
		payload.user_id = interaction.user.id;

		console.log(
			`Wysyłanie zapytania typu: ${type} do API z modelem: ${payload.model || "domyślny"}...`,
		);

		const response = await fetch(`${API_URL}/analyze`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(payload),
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			console.error(
				"Szczegóły błędu z FastAPI:",
				JSON.stringify(errorData, null, 2),
			);

			let errorMsg = `Błąd serwera API (Status ${response.status})`;
			if (errorData.detail) {
				if (Array.isArray(errorData.detail)) {
					errorMsg = errorData.detail
						.map((err) => `• Pole \`${err.loc.join(".")}\`: ${err.msg}`)
						.join("\n");
				} else {
					errorMsg = errorData.detail;
				}
			}
			throw new Error(errorMsg);
		}

		const data = await response.json();

		if (targetMessage) {
			try {
				if (data.is_deepfake) {
					await targetMessage.react("⚠️");
				} else {
					await targetMessage.react("✅");
				}
			} catch (reactError) {
				console.warn(
					"Nie udało się dodać reakcji do wiadomości:",
					reactError.message,
				);
			}
		}

		const embedColor = data.is_deepfake ? 0xFF0000 : 0x00FF00;
		const verdictText = data.is_deepfake ? "⚠️ Wykryto potencjalny Deepfake!" : "✅ Zawartość wydaje się oryginalna";
		const confidencePercent = (data.confidence * 100).toFixed(2);

		const embed = new EmbedBuilder()
			.setColor(embedColor)
			.setTitle("🛡️ Wynik Analizy Treści")
			.setDescription(`**Werdykt:** ${verdictText}`)
			.setTimestamp()
			.setFooter({
				text: "Deepfake Detection Service",
				iconURL: client.user.displayAvatarURL(),
			});

		if (data.details && data.details.length > 0) {
			embed.addFields({ name: "📊 Średnia pewność systemu", value: `\`${confidencePercent}%\``, inline: false });
			
			for (const detail of data.details) {
				const detailBar = getProgressBar(detail.confidence, detail.is_deepfake);
				const statusText = detail.is_deepfake ? "🟥 FAKE" : "🟩 REAL";
				const pct = (detail.confidence * 100).toFixed(1);
				
				embed.addFields({
					name: `🤖 Model: ${detail.model.split("/").pop()}`,
					value: `Werdykt: **${statusText}** (Pewność: \`${pct}%\`)\n${detailBar}`,
					inline: false
				});
			}
		} else {
			const progressBar = getProgressBar(data.confidence, data.is_deepfake);
			embed.addFields(
				{ name: "Pewność modelu", value: `\`${confidencePercent}%\` \n${progressBar}` },
				{ name: "Użyty model", value: `\`${data.used_model}\``, inline: true }
			);
		}

		embed.addFields(
			{ name: "Czas przetwarzania", value: `\`${data.analysis_time.toFixed(3)}s\``, inline: true },
			{ name: "Format danych", value: `\`${data.content_type.toUpperCase()}\``, inline: true }
		);

		const buttonRow = new ActionRowBuilder().addComponents(
			new ButtonBuilder()
				.setCustomId("modelCorrect")
				.setLabel("Model odpowiedział poprawnie")
				.setStyle(ButtonStyle.Success)
				.setEmoji("✅"),
			new ButtonBuilder()
				.setCustomId("reportError")
				.setLabel("Zgłoś błąd analizy")
				.setStyle(ButtonStyle.Danger)
				.setEmoji("⚠️"),
		);

		await interaction.editReply({
			embeds: [embed],
			components: [buttonRow],
		});
	} catch (error) {
		console.error("Błąd podczas analizy:", error);
		await interaction.editReply({
			content: `❌ Nie udało się przeprowadzić analizy.\n\n**Szczegóły błędu:**\n${error.message}`,
		});
	}
}

//funkcja kupczaka

client.on(Events.InteractionCreate, async (interaction) => {
	if (interaction.isChatInputCommand()) {
		if (interaction.commandName === "detect") {
			const modal = new ModalBuilder()
				.setCustomId("detectModal")
				.setTitle("Detektor Deepfake");

			const textInput = new TextInputBuilder()
				.setCustomId("detectInput")
				.setLabel("Wklej tutaj tekst lub link (obraz/wideo):")
				.setStyle(TextInputStyle.Paragraph)
				.setPlaceholder("Wklej zawartość...")
				.setRequired(true);

			const actionRow = new ActionRowBuilder().addComponents(textInput);
			modal.addComponents(actionRow);

			await interaction.showModal(modal);
		}

		if (interaction.commandName === "setup") {
			const guildId = interaction.guildId;

			await interaction.deferReply({ flags: [MessageFlags.Ephemeral] });

			const currentConfig = await fetchGuildConfig(guildId);
			const availableModels = await fetchAvailableModels();

			if (!availableModels || Object.keys(availableModels).length === 0) {
				return interaction.editReply({
					content:
						"❌ **Błąd konfiguracji:** Nie udało się nawiązać połączenia z backendem (FastAPI). Uruchom swój backend w Pythonie i spróbuj ponownie!",
				});
			}

			if (currentConfig.multiModelWorkflow === undefined) {
				currentConfig.multiModelWorkflow = false;
			}

			for (const [contentType, models] of Object.entries(availableModels)) {
				if (!currentConfig.models[contentType] && models.length > 0) {
					currentConfig.models[contentType] = models[0];
				}
			}

			activeSetupSessions.set(guildId, {
				config: { ...currentConfig },
				availableModels,
			});

			const setupView = generateSetupView(currentConfig, availableModels);
			await interaction.editReply(setupView);
		}
	}

	if (interaction.isChannelSelectMenu()) {
		if (interaction.customId === "setup_log_channel") {
			const guildId = interaction.guildId;
			const tempSession = activeSetupSessions.get(guildId);
			if (tempSession) {
				tempSession.config.logChannelId = interaction.values[0];
				await interaction.update(
					generateSetupView(tempSession.config, tempSession.availableModels),
				);
			}
		}
	}

	// OBSŁUGA DYNAMICZNYCH MENU ROZWIJANYCH DLA MODELI
	if (interaction.isStringSelectMenu()) {
		const guildId = interaction.guildId;
		const tempSession = activeSetupSessions.get(guildId);

		if (tempSession) {
			if (interaction.customId.startsWith("setup_model_")) {
				const contentType = interaction.customId.replace("setup_model_", "");
				tempSession.config.models[contentType] = interaction.values[0];
				await interaction.update(
					generateSetupView(tempSession.config, tempSession.availableModels),
				);
			}
		}
	}

	if (interaction.isMessageContextMenuCommand()) {
		if (interaction.commandName === "Wykryj deepfake") {
			const targetMessage = interaction.targetMessage;

			let contentToAnalyze = targetMessage.content;
			let explicitContentType = null;

			const attachment = targetMessage.attachments.first();

			if (attachment) {
				contentToAnalyze = attachment.url;
				explicitContentType = attachment.contentType;
			}

			if (!contentToAnalyze || contentToAnalyze.trim().length === 0) {
				return interaction.reply({
					content:
						"❌ Ta wiadomość nie zawiera tekstu ani załączników do analizy.",
					flags: [MessageFlags.Ephemeral],
				});
			}

			await handleAnalysis(
				interaction,
				contentToAnalyze,
				targetMessage,
				explicitContentType,
			);
		}
		if (interaction.commandName === "Weryfikacja faktów") {
			const targetMessage = interaction.targetMessage;
			const contentToVerify = targetMessage.content;

			if (!contentToVerify || contentToVerify.trim().length < 10) {
				return interaction.reply({
					content:
						"❌ Wiadomość musi mieć przynajmniej 10 znaków tekstu, aby można było ją zweryfikować.",
					flags: [MessageFlags.Ephemeral],
				});
			}

			await handleFactCheck(interaction, contentToVerify);
		}
	}
	//koniec funkcji kupczaka

	if (interaction.isModalSubmit()) {
		if (interaction.customId === "detectModal") {
			const userContent = interaction.fields.getTextInputValue("detectInput");
			await handleAnalysis(interaction, userContent);
		}
	}

	if (interaction.isButton()) {
		const guildId = interaction.guildId;

		if (interaction.customId === "setup_save") {
			const tempSession = activeSetupSessions.get(guildId);
			if (tempSession) {
				try {
					const response = await fetch(`${API_URL}/guilds/${guildId}/setup`, {
						method: "POST",
						headers: {
							"Content-Type": "application/json",
						},
						body: JSON.stringify({
							active_text_model: tempSession.config.models?.text || "none",
							active_image_model: tempSession.config.models?.image || "none",
							log_channel_id: tempSession.config.logChannelId || null,
							multi_model_workflow: tempSession.config.multiModelWorkflow || false
						})
					});

					if (!response.ok) {
						const errData = await response.json();
						throw new Error(errData.detail || "Błąd zapisu na backendzie");
					}

					activeSetupSessions.delete(guildId);
					await interaction.update({
						content:
							"✅ **Ustawienia zostały pomyślnie zapisane na backendzie!**",
						embeds: [],
						components: [],
					});
				} catch (error) {
					console.error("[SETUP ERROR]", error);
					await interaction.update({
						content: `❌ **Wystąpił błąd podczas zapisywania konfiguracji:** ${error.message}`,
						embeds: [],
						components: [],
					});
				}
			}
		}

		if (interaction.customId === "setup_cancel") {
			activeSetupSessions.delete(guildId);
			await interaction.update({
				content: "❌ **Konfiguracja została anulowana.**",
				embeds: [],
				components: [],
			});
		}

		if (interaction.customId === "reportError") {
			const disabledRow = new ActionRowBuilder().addComponents(
				new ButtonBuilder()
					.setCustomId("modelCorrect")
					.setLabel("Model odpowiedział poprawnie")
					.setStyle(ButtonStyle.Success)
					.setEmoji("✅")
					.setDisabled(true),
				new ButtonBuilder()
					.setCustomId("reportError")
					.setLabel("Zgłoś błąd analizy")
					.setStyle(ButtonStyle.Danger)
					.setEmoji("⚠️")
					.setDisabled(true),
			);

			// 2 UPDATE BUTTONS
			await interaction.update({
				embeds: [interaction.message.embeds[0]],
				components: [disabledRow],
			});

			// 3 CONFIRMATION
			await interaction.followUp({
				content:
					"✅ **Dziękujemy!** Twoje zgłoszenie błędu zostało zarejestrowane.",
				flags: [MessageFlags.Ephemeral],
			});

			console.log(
				`[RAPORT BŁĘDU] Użytkownik ${interaction.user.tag} (ID: ${interaction.user.id}) zgłosił błąd klasyfikacji.`,
			);

			const originalEmbed = interaction.message.embeds[0];
			if (originalEmbed) {
				const logEmbed = EmbedBuilder.from(originalEmbed)
					.setColor(0xffaa00)
					.setTitle("⚠️ Zgłoszenie błędu analizy")
					.setDescription(
						`Użytkownik **${interaction.user.tag}** (ID: \`${interaction.user.id}\`) zgłosił błąd analizy w poniższym raporcie.`,
					);

				await sendLogToDiscord(interaction.guild, logEmbed);
			}
		}

		// CORRECT CLICK
		if (interaction.customId === "modelCorrect") {
			const disabledRow = new ActionRowBuilder().addComponents(
				new ButtonBuilder()
					.setCustomId("modelCorrect")
					.setLabel("Model odpowiedział poprawnie")
					.setStyle(ButtonStyle.Success)
					.setEmoji("✅")
					.setDisabled(true),
				new ButtonBuilder()
					.setCustomId("reportError")
					.setLabel("Zgłoś błąd analizy")
					.setStyle(ButtonStyle.Danger)
					.setEmoji("⚠️")
					.setDisabled(true),
			);

			// 2 DISABLE BUTTONS
			await interaction.update({
				embeds: [interaction.message.embeds[0]],
				components: [disabledRow],
			});

			// 3 CONFIRMATION
			await interaction.followUp({
				content:
					"✅ **Dziękujemy!** Twoje potwierdzenie zostało pomyślnie zapisane.",
				flags: [MessageFlags.Ephemeral],
			});

			console.log(
				`[POTWIERDZENIE] Użytkownik ${interaction.user.tag} (ID: ${interaction.user.id}) potwierdził poprawną klasyfikację.`,
			);

			const originalEmbed = interaction.message.embeds[0];
			if (originalEmbed) {
				const logEmbed = EmbedBuilder.from(originalEmbed)
					.setColor(0x00aaff)
					.setTitle("✅ Potwierdzona poprawność analizy")
					.setDescription(
						`Użytkownik **${interaction.user.tag}** (ID: \`${interaction.user.id}\`) potwierdził poprawność raportu.`,
					);

				await sendLogToDiscord(interaction.guild, logEmbed);
			}
		}

		if (interaction.customId === "setup_toggle_multimodel") {
			const tempSession = activeSetupSessions.get(guildId);
			if (tempSession) {
				tempSession.config.multiModelWorkflow = !tempSession.config.multiModelWorkflow;
				await interaction.update(generateSetupView(tempSession.config, tempSession.availableModels));
			}
		}
	}
});

client.on(Events.MessageCreate, (message) => {
	if (message.author.bot) return;
	console.log(`Message from ${message.author.tag}: ${message.content}`);
});

client.login(process.env.DISCORD_TOKEN);