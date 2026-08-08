import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { exec } from "node:child_process";
import { promisify } from "node:util";

const execAsync = promisify(exec);

const server = new McpServer({
  name: "speech-mcp-server",
  version: "1.0.0"
});

server.tool(
  "speak_text",
  "Synthesizes and speaks text out loud through workstation speakers using local C# SpeechApp (Kokoro ONNX engine).",
  {
    text: z.string().describe("The text content to read out loud"),
    voice: z.string().optional().default("am_adam").describe("Voice model profile (default: am_adam)"),
    speed: z.number().optional().default(1.0).describe("Speech speed multiplier (default: 1.0)")
  },
  async ({ text, voice, speed }) => {
    try {
      const exePath = `c:\\dev\\SpeechApp\\bin\\Debug\\net10.0-windows\\SpeechApp.exe`;
      const escapedText = text.replace(/"/g, "");
      const cmd = `"${exePath}" "${escapedText}" "${voice}" "${speed}"`;
      
      const { stdout, stderr } = await execAsync(cmd, {
        env: { ...process.env, FORCE_COLOR: "0" },
        maxBuffer: 10 * 1024 * 1024
      });

      return {
        content: [
          {
            type: "text",
            text: `Speech Output:\n${stdout}\n${stderr ? `Errors:\n${stderr}` : ""}`
          }
        ]
      };
    } catch (err: any) {
      return {
        isError: true,
        content: [
          {
            type: "text",
            text: `Speech Synthesis Failed: ${err.message || String(err)}`
          }
        ]
      };
    }
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Speech MCP Server running on stdio");
}

main().catch((err) => {
  console.error("Fatal error in Speech MCP Server:", err);
  process.exit(1);
});
