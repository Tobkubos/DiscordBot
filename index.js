import dotenv from "dotenv";
dotenv.config();

import { Client, GatewayIntentBits, Events } from "discord.js";

const client = new Client({
	intents: [
		GatewayIntentBits.Guilds,
		GatewayIntentBits.GuildMessages,
		GatewayIntentBits.MessageContent,
	],
});

client.once(Events.ClientReady, () => {
	console.log(`Bot ready: ${client.user.tag}`);
});

client.on(Events.MessageCreate, (message) => {
	if (message.author.bot) return;
	console.log(`Message from ${message.author.tag}: ${message.content}`);
});

console.log("Wczytany token:", process.env.DISCORD_TOKEN);
client.login(process.env.DISCORD_TOKEN);
