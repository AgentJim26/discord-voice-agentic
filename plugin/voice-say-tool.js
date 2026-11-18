export function registerDiscordVoiceSayTool(api) {
	api.registerTool(() => ({
		name: "discord_voice_say",
		label: "Discord Voice Say",
		description: "Speak text aloud in a Discord voice channel via TTS. Joins the configured voice channel if not already connected. Use this when asked to say something in a Discord voice channel.",
		parameters: {
			type: "object",
			properties: {
				text: {
					type: "string",
					description: "Text to speak aloud."
				},
				guildId: {
					type: "string",
					description: "Discord guild ID. Defaults to the active voice session or the only configured guild."
				},
				channelId: {
					type: "string",
					description: "Discord voice channel ID. Defaults to the active or configured channel."
				}
			},
			required: ["text"],
			additionalProperties: false
		},
		execute: async (_toolCallId, params) => {
			const managers = globalThis.__openclawDiscordVoiceManagers;
			const manager = managers instanceof Map ? managers.values().next().value : null;
			if (!manager) return { content: [{ type: "text", text: "Discord voice manager is not running." }] };
			try {
				const result = await manager.speak(params ?? {});
				return {
					content: [{ type: "text", text: JSON.stringify(result) }],
					details: result
				};
			} catch (error) {
				return { content: [{ type: "text", text: `Voice speak failed: ${error?.message ?? error}` }] };
			}
		}
	}), { name: "discord_voice_say" });
}
