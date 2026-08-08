# speech-mcp-server

![Speech MCP Server Banner](./speech_mcp_banner.jpg)

Local Stdio Model Context Protocol (MCP) server wrapping the **Kokoro ONNX Neural TTS Engine** with real-time **Voice Vector Algebra**, **Central Wisconsin Vernacular Lexicon Overrides**, and **thread-clamped zero-VRAM CPU execution**.

> *"Neural voice vectors mixed mathematically. Zero VRAM overhead. Pure local performance."*

---

## 🔊 Key Architectural Features

- **Voice Vector Algebra Engine**: Mix multiple voice profiles using linear vector algebra directly in Python:
  $$\text{Voice} = (\text{am\_adam} \times 0.65) + (\text{bm\_lewis} \times 0.30) + (\text{am\_michael} \times 0.05)$$
- **Central Wisconsin Vernacular Dict**: Built-in phonetic lexicon mapper enforcing regional dialect pacing and word pronunciations (`bag` $\to$ `bayg`, `roof` $\to$ `ruff`, `creek` $\to$ `crick`, `know'm'sayin`).
- **Zero GPU VRAM Overhead**: Operates entirely on CPU via ONNX Runtime Execution Provider. Keeps GPU completely idle (0% load, 0 MB VRAM).
- **Thread-Clamped CPU Execution**: Throttled to 2 worker threads (`OMP_NUM_THREADS = 2`) to eliminate CPU spikes while maintaining sub-200ms latency.
- **Kokoro ONNX Engine**: High-fidelity 24kHz neural TTS with multiple base voice profiles (`am_adam`, `af_bella`, `bm_lewis`, `am_michael`).
- **MCP Stdio Transport**: Full Model Context Protocol compatibility for AI agents and LLM tool integration (`/speak`).

---

## 🚀 Quickstart

### Prerequisites
- Node.js v18+
- Python 3.10+ with `kokoro-onnx`, `onnxruntime`, `soundfile`, `numpy`

### Installation & Build
```bash
git clone https://github.com/yavru421/speech-mcp-server.git
cd speech-mcp-server
npm install
npm run build
```

### Usage
```bash
python synth.py "Lexicon overrides active for DuckDB and WASAPI." "am_adam*0.65 + bm_lewis*0.30" "0.94"
```

### Configuration (MCP Client)
Add to your `mcpServers` configuration:
```json
{
  "speech-mcp-server": {
    "command": "node",
    "args": ["<path_to_repo>/build/index.js"]
  }
}
```

---

## 🔒 License
MIT
