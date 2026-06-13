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
  MessageFlags 
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
			},
		]);
		console.log("Pomyślnie zarejestrowano komendę /detect");
	} catch (error) {
		console.error("Błąd podczas rejestracji komendy:", error);
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

	if (interaction.isModalSubmit()) {
		if (interaction.customId === "detectModal") {
			const userContent = interaction.fields.getTextInputValue("detectInput");

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

				const statusEmoji = data.is_deepfake ? "⚠️ **Wykryto potencjalny Deepfake!**" : "✅ **Zawartość wydaje się oryginalna**";
				const confidencePercent = (data.confidence * 100).toFixed(2);
				const timeSec = data.analysis_time.toFixed(3);

				const replyMessage = 
					`### Wyniki Analizy (${data.content_type.toUpperCase()})\n` +
					`${statusEmoji}\n\n` +
					`* **Pewność modelu:** \`${confidencePercent}%\`\n` +
					`* **Użyty model:** \`${data.used_model}\`\n` +
					`* **Czas przetwarzania:** \`${timeSec} sekund\`\n`;

				await interaction.editReply({
					content: replyMessage,
				});

			} catch (error) {
				console.error("Błąd podczas analizy:", error);
				await interaction.editReply({
					content: `❌ Nie udało się przeprowadzić analizy.\n\n**Szczegóły błędu:**\n${error.message}`,
				});
			}
		}
	}
});

client.on(Events.MessageCreate, (message) => {
	if (message.author.bot) return;
	console.log(`Message from ${message.author.tag}: ${message.content}`);
});

client.login(process.env.DISCORD_TOKEN);