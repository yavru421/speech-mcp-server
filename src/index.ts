import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { exec } from "node:child_process";
import { promisify } from "node:util";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const execAsync = promisify(exec);
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const server = new McpServer({
  name: "speech-mcp-server",
  version: "1.0.0"
});

server.tool(
  "speak_text",
  "Synthesizes and speaks text out loud through workstation speakers using local C# SpeechApp (Kokoro ONNX engine).",
  {
    text: z.string().describe("The text content to read out loud"),
    voice: z.string().optional().default("am_adam*0.65 + bm_lewis*0.30 + am_michael*0.05").describe("Voice model profile expression"),
    speed: z.number().optional().default(0.95).describe("Speech speed multiplier (default: 0.95)")
  },
  async ({ text, voice, speed }) => {
    try {
      const synthScript = join(__dirname, "..", "synth.py");
      const pythonExe = "C:\\Miniforge\\python.exe";
      const escapedText = text.replace(/"/g, '\\"');
      const cmd = `"${pythonExe}" "${synthScript}" "${escapedText}" "${voice}" "${speed}"`;
      
      const { stdout, stderr } = await execAsync(cmd, {
        env: { ...process.env, FORCE_COLOR: "0" },
        maxBuffer: 10 * 1024 * 1024
      });

      const match = stdout.match(/SYNTH_WAV:(.+)/);
      if (match && match[1]) {
        const wavPath = match[1].trim();
        await execAsync(`powershell -c "(New-Object Media.SoundPlayer '${wavPath}').PlaySync()"`);
      }

      return {
        content: [
          {
            type: "text",
            text: `Speech Output (Kokoro ONNX):\n${stdout}\n${stderr ? `Errors:\n${stderr}` : ""}`
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
