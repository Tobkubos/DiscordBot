import dotenv from "dotenv";
dotenv.config();

import { 
  Client, 
  GatewayIntentBits, 
  Events, 
  ModalBuilder, 
  TextInputBuilder, 
  TextInputStyle, 
  ActionRowBuilder 
} from "discord.js";

const client = new Client({
	intents: [
		GatewayIntentBits.Guilds,
		GatewayIntentBits.GuildMessages,
		GatewayIntentBits.MessageContent,
	],
});

client.once(Events.ClientReady, async () => {
	console.log(`Bot ready: ${client.user.tag}`);

	try {
		await client.application.commands.set([
			{
				name: "detect",
				description: "Otwiera okienko do wklejenia linku lub tekstu",
			},
		]);
		console.log("Pomyślnie zarejestrowano komendę /detect");
	} catch (error) {
		console.error("Błąd podczas rejestracji komendy:", error);
	}
});

client.on(Events.InteractionCreate, async (interaction) => {
	
	if (interaction.isChatInputCommand()) {
		if (interaction.commandName === "detect") {
			
			const modal = new ModalBuilder()
				.setCustomId("detectModal")
				.setTitle("Detektor linków/tekstu");

			const textInput = new TextInputBuilder()
				.setCustomId("detectInput")
				.setLabel("Wklej tutaj link lub tekst do przetworzenia:")
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

			await interaction.reply({
				content: `ziemniak`,
				ephemeral: true, 
			});

			console.log(`Użytkownik wkleił: ${userContent}`);
		}
	}
});

client.on(Events.MessageCreate, (message) => {
	if (message.author.bot) return;
	console.log(`Message from ${message.author.tag}: ${message.content}`);
});

client.login(process.env.DISCORD_TOKEN);