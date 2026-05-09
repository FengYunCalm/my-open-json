import type { Plugin, PluginModule } from "@opencode-ai/plugin"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"

// RTK OpenCode plugin — rewrites commands to use rtk for token savings.
// Requires: rtk >= 0.23.0 in PATH or ~/.local/bin/rtk.
//
// This is a thin delegating plugin: all rewrite logic lives in `rtk rewrite`,
// which is the single source of truth (src/discover/registry.rs).
// To add or change rewrite rules, edit the Rust registry — not this file.

export const RtkOpenCodePlugin: Plugin = async ({ $ }) => {
  const isExecutable = (candidate: string) => {
    try {
      fs.accessSync(candidate, fs.constants.X_OK)
      return true
    } catch {
      return false
    }
  }

  const candidates = new Set<string>()

  for (const dir of (process.env.PATH ?? "").split(path.delimiter)) {
    if (dir) candidates.add(path.join(dir, "rtk"))
  }

  if (process.env.RTK_BIN) candidates.add(process.env.RTK_BIN)
  candidates.add(path.join(os.homedir(), ".local", "bin", "rtk"))

  const rtkBinary = [...candidates].find(isExecutable)

  if (!rtkBinary) {
    console.warn("[rtk] rtk binary not found in PATH or ~/.local/bin — plugin disabled")
    return {}
  }

  return {
    "tool.execute.before": async (input, output) => {
      const tool = String(input?.tool ?? "").toLowerCase()
      if (tool !== "bash" && tool !== "shell") return
      const args = output?.args
      if (!args || typeof args !== "object") return

      const command = (args as Record<string, unknown>).command
      if (typeof command !== "string" || !command) return

      try {
        const result = await $`${rtkBinary} rewrite ${command}`.quiet().nothrow()
        const rewritten = String(result.stdout).trim()
        if (rewritten && rewritten !== command) {
          ;(args as Record<string, unknown>).command = rewritten
        }
      } catch {
        // rtk rewrite failed — pass through unchanged
      }
    },
  }
}

export default {
  id: "rtk",
  server: RtkOpenCodePlugin,
} satisfies PluginModule
