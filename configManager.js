import fs from "fs";
import path from "path";

const filePath = path.resolve("./guildConfigs.json");

// Domyślne ustawienia (teraz modele są zapisywane dynamicznie w obiekcie)
export const DEFAULT_CONFIG = {
	logChannelId: null,
	models: {} 
};

export function loadConfig(guildId) {
	if (!fs.existsSync(filePath)) {
		fs.writeFileSync(filePath, JSON.stringify({}));
	}
	try {
		const data = JSON.parse(fs.readFileSync(filePath, "utf-8"));
		const config = data[guildId] || { ...DEFAULT_CONFIG };
		
		// Upewniamy się, że obiekt "models" zawsze istnieje
		if (!config.models) {
			config.models = {};
		}
		return config;
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