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
  ButtonStyle
} from "discord.js";

const client = new Client({
	intents: [
		GatewayIntentBits.Guilds,
		GatewayIntentBits.GuildMessages,
		GatewayIntentBits.MessageContent,
	],
});

const API_URL = process.env.API_URL || "http://127.0.0.1:8000";

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
				name: "Przeanalizuj tekst",
				type: ApplicationCommandType.Message
			}
		]);
		console.log("Pomyślnie zarejestrowano komendy (/detect oraz menu kontekstowe)");
	} catch (error) {
		console.error("Błąd podczas rejestracji komend:", error);
	}
});

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

async function handleAnalysis(interaction, userContent, targetMessage = null) {
	await interaction.deferReply({ flags: [MessageFlags.Ephemeral] });

	try {
		const { type, payload } = preparePayload(userContent);
		
		console.log(`Wysyłanie zapytania typu: ${type} do API...`);

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
				{ name: "Użyty model", value: `\`${data.model_used}\``, inline: true },
				{ name: "Format danych", value: `\`${data.content_type.toUpperCase()}\``, inline: true }
			)
			.setTimestamp()
			.setFooter({ text: "Deepfake Detection Service", iconURL: client.user.displayAvatarURL() });

		// TWORZENIE PRZYCISKÓW
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

	// GUZIKI
	if (interaction.isButton()) {
		// ZGŁOSZENIE BŁĘDU
		if (interaction.customId === "reportError") {
			await interaction.reply({
				content: "✅ **Dziękujemy!** Twoje zgłoszenie błędu zostało zarejestrowane. Pomoże nam ono udoskonalić algorytmy detekcji.",
				flags: [MessageFlags.Ephemeral]
			});

			console.log(`[RAPORT BŁĘDU] Użytkownik ${interaction.user.tag} (ID: ${interaction.user.id}) zgłosił błędną klasyfikację bota.`);
		}

		// POTWIERDZENIE POPRAWNOŚCI
		if (interaction.customId === "modelCorrect") {
			await interaction.reply({
				content: "✅ **Dziękujemy!** Twoje potwierdzenie zostało pomyślnie zapisane. Cieszymy się, że model zadziałał prawidłowo.",
				flags: [MessageFlags.Ephemeral]
			});

			console.log(`[POTWIERDZENIE] Użytkownik ${interaction.user.tag} (ID: ${interaction.user.id}) potwierdził poprawną klasyfikację bota.`);
		}
	}
});

client.on(Events.MessageCreate, (message) => {
	if (message.author.bot) return;
	console.log(`Message from ${message.author.tag}: ${message.content}`);
});

client.login(process.env.DISCORD_TOKEN);