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
  ChannelType
} from "discord.js";

import { loadConfig, saveConfig } from "./configManager.js";

const client = new Client({
	intents: [
		GatewayIntentBits.Guilds,
		GatewayIntentBits.GuildMessages,
		GatewayIntentBits.MessageContent,
	],
});

const API_URL = process.env.API_URL || "http://127.0.0.1:8000";

// Domyślne modele zapasowe (używane gdyby backend był wyłączony podczas konfiguracji)
const FALLBACK_MODELS = {
	text: ["yaya36095/xlm-roberta-text-detector", "mock"],
	image: ["capcheck/ai-image-detection", "mock"]
};

// Pamięć podręczna przechowuje konfigurację oraz pobrane dynamicznie modele
const activeSetupSessions = new Map();

client.once(Events.ClientReady, async () => {
	console.log(`Bot ready: ${client.user.tag}`);

	try {
		await client.application.commands.set([
			{
				name: "detect",
				description: "Otwiera okienko do wklejenia linku lub tekstu do analizy",
				type: ApplicationCommandType.ChatInput
			},
			{
				name: "setup",
				description: "Ustawienia kanału logów i modeli analizy (Wymaga Administratora)",
				default_member_permissions: PermissionFlagsBits.Administrator.toString(),
				type: ApplicationCommandType.ChatInput
			},
			{
				name: "Przeanalizuj tekst",
				type: ApplicationCommandType.Message
			}
		]);
		console.log("Pomyślnie zarejestrowano komendy (/detect, /setup oraz menu kontekstowe)");
	} catch (error) {
		console.error("Błąd podczas rejestracji komend:", error);
	}
});

// Funkcja pobierająca aktualne modele bezpośrednio z FastAPI w czasie rzeczywistym
async function fetchAvailableModels() {
	try {
		const response = await fetch(API_URL);
		if (response.ok) {
			const data = await response.json();
			if (data.available_models) {
				const textModels = data.available_models.text || [];
				const imageModels = data.available_models.image || [];

				// Upewniamy się, że zawsze mamy opcję testową "mock"
				if (!textModels.includes("mock")) textModels.push("mock");
				if (!imageModels.includes("mock")) imageModels.push("mock");

				return { text: textModels, image: imageModels };
			}
		}
	} catch (err) {
		console.warn("Nie udało się pobrać modeli z API (użyto modeli zapasowych):", err.message);
	}
	return FALLBACK_MODELS;
}

function preparePayload(input) {
	const trimmed = input.trim();
	const isUrl = trimmed.startsWith("http://") || trimmed.startsWith("https://");

	if (isUrl) {
		const lowerUrl = trimmed.toLowerCase();
		
		if (lowerUrl.endsWith(".png") || lowerUrl.endsWith(".jpg") || lowerUrl.endsWith(".jpeg") || lowerUrl.endsWith(".webp") || lowerUrl.endsWith(".gif")) {
			return { 
				type: "image", 
				payload: { 
					image_url: trimmed,
					content_type: "image"
				} 
			};
		} else if (lowerUrl.endsWith(".mp4") || lowerUrl.endsWith(".webm") || lowerUrl.endsWith(".mov") || lowerUrl.endsWith(".avi")) {
			return { 
				type: "video", 
				payload: { 
					video_url: trimmed,
					content_type: "video"
				} 
			};
		} else {
			return { 
				type: "file", 
				payload: { 
					file_url: trimmed,
					content_type: "file"
				} 
			};
		}
	}

	return { 
		type: "text", 
		payload: { 
			text: trimmed,
			content_type: "text"
		} 
	};
}

function getProgressBar(confidence, isDeepfake) {
	const totalBlocks = 10;
	const filledBlocks = Math.min(totalBlocks, Math.max(0, Math.round(confidence * totalBlocks)));
	const emptyBlocks = totalBlocks - filledBlocks;
	const blockEmoji = isDeepfake ? "🟥" : "🟩";
	return blockEmoji.repeat(filledBlocks) + "⬛".repeat(emptyBlocks);
}

// ZMIANA: Funkcja przyjmuje teraz pobrane dynamicznie modele jako drugi parametr
function generateSetupView(tempConfig, availableModels) {
	const embed = new EmbedBuilder()
		.setColor(0x5865F2)
		.setTitle("⚙️ Konfiguracja Systemu Detekcji")
		.setDescription("Wybierz kanał do wysyłania logów oraz aktywne modele analizy z menu poniżej.")
		.addFields(
			{ 
				name: "📂 Kanał logów (Raporty)", 
				value: tempConfig.logChannelId ? `<#${tempConfig.logChannelId}>` : "*Wysyłanie tylko do konsoli*", 
				inline: false 
			},
			{ 
				name: "📝 Model tekstowy", 
				value: `\`${tempConfig.textModel}\``, 
				inline: true 
			},
			{ 
				name: "🖼️ Model obrazów", 
				value: `\`${tempConfig.imageModel}\``, 
				inline: true 
			}
		)
		.setFooter({ text: "Wybierz opcje i kliknij Zapisz ustawienia" })
		.setTimestamp();

	const channelSelect = new ChannelSelectMenuBuilder()
		.setCustomId("setup_log_channel")
		.setPlaceholder("Wybierz kanał dla raportów")
		.addChannelTypes(ChannelType.GuildText);

	// DYNAMICZNE mapowanie modeli tekstowych z API
	const textOptions = availableModels.text.map(model => ({
		label: model === "mock" ? "Mock (Model testowy)" : model,
		value: model,
		default: tempConfig.textModel === model
	}));

	const textModelSelect = new StringSelectMenuBuilder()
		.setCustomId("setup_text_model")
		.setPlaceholder("Wybierz model tekstu")
		.addOptions(textOptions);

	// DYNAMICZNE mapowanie modeli graficznych z API
	const imageOptions = availableModels.image.map(model => ({
		label: model === "mock" ? "Mock (Model testowy)" : model,
		value: model,
		default: tempConfig.imageModel === model
	}));

	const imageModelSelect = new StringSelectMenuBuilder()
		.setCustomId("setup_image_model")
		.setPlaceholder("Wybierz model obrazów")
		.addOptions(imageOptions);

	const buttonsRow = new ActionRowBuilder().addComponents(
		new ButtonBuilder()
			.setCustomId("setup_save")
			.setLabel("Zapisz ustawienia")
			.setStyle(ButtonStyle.Success)
			.setEmoji("💾"),
		new ButtonBuilder()
			.setCustomId("setup_cancel")
			.setLabel("Anuluj")
			.setStyle(ButtonStyle.Danger)
			.setEmoji("❌")
	);

	return {
		embeds: [embed],
		components: [
			new ActionRowBuilder().addComponents(channelSelect),
			new ActionRowBuilder().addComponents(textModelSelect),
			new ActionRowBuilder().addComponents(imageModelSelect),
			buttonsRow
		]
	};
}

async function sendLogToDiscord(guild, embedToSend) {
	const config = loadConfig(guild.id);
	if (!config.logChannelId) return;

	try {
		const channel = await guild.channels.fetch(config.logChannelId);
		if (channel) {
			await channel.send({ embeds: [embedToSend] });
		}
	} catch (err) {
		console.warn(`Nie można wysłać logu na kanał ${config.logChannelId}:`, err.message);
	}
}

async function handleAnalysis(interaction, userContent, targetMessage = null) {
	await interaction.deferReply({ flags: [MessageFlags.Ephemeral] });

	const serverConfig = loadConfig(interaction.guildId);

	try {
		const { type, payload } = preparePayload(userContent);
		
		if (type === "text") {
			payload.model = serverConfig.textModel;
		} else if (type === "image") {
			payload.model = serverConfig.imageModel;
		}

		console.log(`Wysyłanie zapytania typu: ${type} do API z modelem: ${payload.model}...`);

		const response = await fetch(`${API_URL}/analyze`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(payload),
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			console.error("Szczegóły błędu z FastAPI:", JSON.stringify(errorData, null, 2));
			
			let errorMsg = `Błąd serwera API (Status ${response.status})`;
			if (errorData.detail) {
				if (Array.isArray(errorData.detail)) {
					errorMsg = errorData.detail
						.map(err => `• Pole \`${err.loc.join(".")}\`: ${err.msg}`)
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
					await targetMessage.react('⚠️');
				} else {
					await targetMessage.react('✅');
				}
			} catch (reactError) {
				console.warn("Nie udało się dodać reakcji do wiadomości:", reactError.message);
			}
		}

		const embedColor = data.is_deepfake ? 0xFF0000 : 0x00FF00;
		const verdictText = data.is_deepfake ? "⚠️ Wykryto potencjalny Deepfake!" : "✅ Zawartość wydaje się oryginalna";
		const progressBar = getProgressBar(data.confidence, data.is_deepfake);
		const confidencePercent = (data.confidence * 100).toFixed(2);

		const embed = new EmbedBuilder()
			.setColor(embedColor)
			.setTitle("🛡️ Wynik Analizy Treści")
			.setDescription(`**Werdykt:** ${verdictText}`)
			.addFields(
				{ name: "Pewność modelu", value: `\`${confidencePercent}%\` \n${progressBar}` },
				{ name: "Czas przetwarzania", value: `\`${data.analysis_time.toFixed(3)}s\``, inline: true },
				{ name: "Użyty model", value: `\`${data.used_model}\``, inline: true },
				{ name: "Format danych", value: `\`${data.content_type.toUpperCase()}\``, inline: true }
			)
			.setTimestamp()
			.setFooter({ text: "Deepfake Detection Service", iconURL: client.user.displayAvatarURL() });

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
				.setEmoji("⚠️")
		);

		await interaction.editReply({
			embeds: [embed],
			components: [buttonRow]
		});

	} catch (error) {
		console.error("Błąd podczas analizy:", error);
		await interaction.editReply({
			content: `❌ Nie udało się przeprowadzić analizy.\n\n**Szczegóły błędu:**\n${error.message}`,
		});
	}
}

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

		// ZMIANA: Pobieranie modeli z API na żywo przed pokazaniem setupu
		if (interaction.commandName === "setup") {
			const guildId = interaction.guildId;
			const currentConfig = loadConfig(guildId);

			// Informujemy Discord, że pobieramy konfigurację z API
			await interaction.deferReply({ flags: [MessageFlags.Ephemeral] });

			// Pobieramy aktywne modele bezpośrednio z FastAPI
			const availableModels = await fetchAvailableModels();

			// Zapisujemy w sesji zarówno konfigurację, jak i pobrane modele
			activeSetupSessions.set(guildId, { 
				config: { ...currentConfig }, 
				availableModels 
			});

			const setupView = generateSetupView(currentConfig, availableModels);
			await interaction.editReply(setupView);
		}
	}

	// OBSŁUGA ZMIANY KANAŁU LOGÓW
	if (interaction.isChannelSelectMenu()) {
		if (interaction.customId === "setup_log_channel") {
			const guildId = interaction.guildId;
			const tempSession = activeSetupSessions.get(guildId);
			if (tempSession) {
				tempSession.config.logChannelId = interaction.values[0];
				await interaction.update(generateSetupView(tempSession.config, tempSession.availableModels));
			}
		}
	}

	// OBSŁUGA ZMIANY MODELI
	if (interaction.isStringSelectMenu()) {
		const guildId = interaction.guildId;
		const tempSession = activeSetupSessions.get(guildId);
		
		if (tempSession) {
			if (interaction.customId === "setup_text_model") {
				tempSession.config.textModel = interaction.values[0];
			} else if (interaction.customId === "setup_image_model") {
				tempSession.config.imageModel = interaction.values[0];
			}
			await interaction.update(generateSetupView(tempSession.config, tempSession.availableModels));
		}
	}

	if (interaction.isMessageContextMenuCommand()) {
		if (interaction.commandName === "Przeanalizuj tekst") {
			const targetMessage = interaction.targetMessage;
			
			let contentToAnalyze = targetMessage.content;
			const attachment = targetMessage.attachments.first();
			
			if (attachment) {
				contentToAnalyze = attachment.url;
			}

			if (!contentToAnalyze || contentToAnalyze.trim().length === 0) {
				return interaction.reply({
					content: "❌ Ta wiadomość nie zawiera tekstu ani załączników do analizy.",
					flags: [MessageFlags.Ephemeral]
				});
			}

			await handleAnalysis(interaction, contentToAnalyze, targetMessage);
		}
	}

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
				saveConfig(guildId, tempSession.config);
				activeSetupSessions.delete(guildId);
				await interaction.update({
					content: "✅ **Ustawienia zostały pomyślnie zapisane!**",
					embeds: [],
					components: []
				});
			}
		}

		if (interaction.customId === "setup_cancel") {
			activeSetupSessions.delete(guildId);
			await interaction.update({
				content: "❌ **Konfiguracja została anulowana.**",
				embeds: [],
				components: []
			});
		}

		if (interaction.customId === "reportError") {
			await interaction.reply({
				content: "✅ **Dziękujemy!** Twoje zgłoszenie błędu zostało zarejestrowane.",
				flags: [MessageFlags.Ephemeral]
			});

			console.log(`[RAPORT BŁĘDU] Użytkownik ${interaction.user.tag} (ID: ${interaction.user.id}) zgłosił błędną klasyfikację.`);

			const originalEmbed = interaction.message.embeds[0];
			if (originalEmbed) {
				const logEmbed = EmbedBuilder.from(originalEmbed)
					.setColor(0xFFAA00)
					.setTitle("⚠️ Zgłoszenie błędu analizy")
					.setDescription(`Użytkownik **${interaction.user.tag}** (ID: \`${interaction.user.id}\`) zgłosił błąd analizy w poniższym raporcie.`);
				
				await sendLogToDiscord(interaction.guild, logEmbed);
			}
		}

		if (interaction.customId === "modelCorrect") {
			await interaction.reply({
				content: "✅ **Dziękujemy!** Twoje potwierdzenie zostało pomyślnie zapisane.",
				flags: [MessageFlags.Ephemeral]
			});

			console.log(`[POTWIERDZENIE] Użytkownik ${interaction.user.tag} (ID: ${interaction.user.id}) potwierdził poprawną klasyfikację.`);

			const originalEmbed = interaction.message.embeds[0];
			if (originalEmbed) {
				const logEmbed = EmbedBuilder.from(originalEmbed)
					.setColor(0x00AAFF)
					.setTitle("✅ Potwierdzona poprawność analizy")
					.setDescription(`Użytkownik **${interaction.user.tag}** (ID: \`${interaction.user.id}\`) potwierdził poprawność raportu.`);
				
				await sendLogToDiscord(interaction.guild, logEmbed);
			}
		}
	}
});

client.on(Events.MessageCreate, (message) => {
	if (message.author.bot) return;
	console.log(`Message from ${message.author.tag}: ${message.content}`);
});

client.login(process.env.DISCORD_TOKEN);