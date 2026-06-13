import { EmbedBuilder, MessageFlags } from "discord.js";

const API_URL = process.env.API_URL || "http://127.0.0.1:8000";
let lastFactCheckTime = 0;
const COOLDOWN_MS = 5000;

export async function handleFactCheck(interaction) {
    const now = Date.now();
    
    if (now - lastFactCheckTime < COOLDOWN_MS) {
        return interaction.reply({
            content: "⏳ System zajęty: Bot weryfikuje inną wiadomość. Spróbuj za chwilę.",
            flags: [MessageFlags.Ephemeral]
        });
    }

    const targetMessage = interaction.targetMessage;
    const content = targetMessage.content ? targetMessage.content.trim() : "";
    
    if (!content || content.length < 10) {
        return interaction.reply({
            content: "❌ Wiadomość jest zbyt krótka. Podaj konkretną tezę do weryfikacji.",
            flags: [MessageFlags.Ephemeral]
        });
    }

    lastFactCheckTime = now;
    await interaction.deferReply(); 

    try {
        const response = await fetch(`${API_URL}/factcheck`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: content }),
        });

        if (!response.ok) throw new Error("Błąd serwera API");

        const data = await response.json();

        let embedColor = 0xFFA500; // Pomarańczowy dla "SPORNE"
        if (data.verdict === "PRAWDA") embedColor = 0x00FF00;
        if (data.verdict === "FAŁSZ") embedColor = 0xFF0000;
        
        const sourcesText = data.sources && data.sources.length > 0 
            ? data.sources.join("\n") 
            : "Brak bezpośrednich linków";

        const embed = new EmbedBuilder()
            .setColor(embedColor)
            .setTitle("🔍 Weryfikacja Faktów")
            .setDescription(`**Werdykt:** ${data.verdict}\n\n**Uzasadnienie:**\n${data.explanation}`)
            .addFields({ name: "Wykorzystane źródła", value: sourcesText })
            .setTimestamp()
            .setFooter({ text: "Analiza na żywo za pomocą Llama 3 & DuckDuckGo" });

        await interaction.editReply({ embeds: [embed] });

    } catch (error) {
        console.error("Błąd fack-checkingu:", error);
        await interaction.editReply("❌ Serwer napotkał błąd podczas analizy. Sprawdź, czy backend jest uruchomiony.");
    }
}