process.env.RELAY_MCP_DATABASE_PATH ||= "/home/mechrevo/.config/opencode/plugins/opencode-a2a-relay.sqlite";

await import("./opencode-a2a-relay-mcp.bundle.js");
