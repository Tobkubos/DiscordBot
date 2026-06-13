import fs from "fs";
import path from "path";

const filePath = path.resolve("./guildConfigs.json");

export const DEFAULT_CONFIG = {
	logChannelId: null,
	textModel: "yaya36095/xlm-roberta-text-detector",
	imageModel: "capcheck/ai-image-detection"
};

export function loadConfig(guildId) {
	if (!fs.existsSync(filePath)) {
		fs.writeFileSync(filePath, JSON.stringify({}));
	}
	try {
		const data = JSON.parse(fs.readFileSync(filePath, "utf-8"));
		return data[guildId] || { ...DEFAULT_CONFIG };
	} catch (err) {
		console.error("Błąd podczas odczytu konfiguracji:", err);
		return { ...DEFAULT_CONFIG };
	}
}

export function saveConfig(guildId, newConfig) {
	if (!fs.existsSync(filePath)) {
		fs.writeFileSync(filePath, JSON.stringify({}));
	}
	try {
		const data = JSON.parse(fs.readFileSync(filePath, "utf-8"));
		data[guildId] = { ...DEFAULT_CONFIG, ...data[guildId], ...newConfig };
		fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
		return true;
	} catch (err) {
		console.error("Błąd podczas zapisu konfiguracji:", err);
		return false;
	}
}