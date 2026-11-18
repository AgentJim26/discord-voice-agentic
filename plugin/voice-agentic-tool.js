export function registerDiscordVoiceAgenticTool(api) {
	api.registerTool(() => ({
		name: "discord_voice_agentic",
		label: "Discord Voice Agentic Mode",
		description: "Turn wake-word agentic voice mode on or off for a Discord voice channel. When on, Jim listens for 'hey Jim' or 'hi Jim' before responding.",
		parameters: {
			type: "object",
			properties: {
				enabled: {
					type: "boolean",
					description: "True to enable wake-word agentic mode, false to disable it."
				},
				guildId: {
					type: "string",
					description: "Discord guild ID. Defaults to the active voice session."
				}
			},
			required: ["enabled"],
			additionalProperties: false
		},
		execute: async (_toolCallId, params) => {
			const managers = globalThis.__openclawDiscordVoiceManagers;
			const manager = managers instanceof Map ? managers.values().next().value : null;
			if (!manager) return { content: [{ type: "text", text: "Discord voice manager is not running." }] };
			const guildId = params?.guildId ?? manager.sessions?.keys?.().next?.().value ?? "1561016783887011941";
			const result = manager.setAgenticMode(guildId, params?.enabled === true);
			return {
				content: [{ type: "text", text: JSON.stringify(result) }],
				details: result
			};
		}
	}), { name: "discord_voice_agentic" });
}
