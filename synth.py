import sys
import os
import re
import time
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

import json

MODEL_PATH = "C:/dev/kokoro-v0_19.onnx"
VOICES_PATH = "C:/dev/voices-v1.0.bin"
PRESETS_DIR = "C:/dev/speech-mcp-server/presets"
LEXICON_JSON = "C:/dev/speech-mcp-server/wisconsin_lexicon.json"

LEXICON_OVERRIDES = {
    "duckdb": "duck D B",
    "wasapi": "Wah-sah-pee",
    "onnx": "Onix",
    "dpapi": "D P A P I",
    "metropolis": "Meh-trop-oh-lis",
    "yeah": "yah",
    "bag": "bayg",
    "bags": "baygz",
    "roof": "ruff",
    "creek": "crick",
    "ope": "ohp",
    "wisconsin": "Wih-scon-sin",
    "bubbler": "buhb-ler",
    "suppose": "s'pose",
    "know what i mean": "know'm'sayin",
    "know what im saying": "know'm'sayin",
    "know what i'm saying": "know'm'sayin"
}

# Clean, subtle Wisconsin/Midwest regional phonetic overrides for Mercy
WISCONSIN_CLEAN_LEXICON = {
    "duckdb": "Duck D B",
    "duck db": "Duck D B",
    "telemetry": "tell-eh-muh-tree",
    "memory": "mem-ree",
    "wisconsin": "Wih-scon-sin",
    "bag": "bayg",
    "bags": "baygz",
    "roof": "ruff",
    "creek": "crick"
}

def get_merged_lexicon(voice_expr=""):
    merged = dict(LEXICON_OVERRIDES)
    if "mercy" in voice_expr.lower():
        merged.update(WISCONSIN_CLEAN_LEXICON)
    if os.path.exists(LEXICON_JSON):
        try:
            with open(LEXICON_JSON, "r", encoding="utf-8") as f:
                geo_lexicon = json.load(f)
                merged.update(geo_lexicon)
        except Exception:
            pass
    return merged

def apply_lexicon_overrides(text, voice_expr=""):
    lexicon = get_merged_lexicon(voice_expr)
    # Sort keys by length descending to replace multi-word entries first
    sorted_keys = sorted(lexicon.keys(), key=len, reverse=True)
    for key in sorted_keys:
        pattern = r'\b' + re.escape(key) + r'\b'
        text = re.sub(pattern, lexicon[key], text, flags=re.IGNORECASE)
    return text

def parse_voice_algebra(kokoro, voice_expr):
    os.makedirs(PRESETS_DIR, exist_ok=True)
    v_clean = voice_expr.strip().lower()
    
    preset_file = os.path.join(PRESETS_DIR, f"{v_clean}.npy")
    if os.path.exists(preset_file):
        return np.load(preset_file)

    if v_clean in ("gideon", "default"):
        voice_expr = "am_adam*0.65 + bm_lewis*0.30 + am_michael*0.05"
    elif v_clean == "malachi":
        voice_expr = "am_michael*0.60 + bm_george*0.30 + am_adam*0.10"
    elif v_clean == "santa_anna":
        voice_expr = "af_sky*0.60 + af_bella*0.40"
    elif v_clean == "mercy":
        # Low, articulate Wisconsin/Midwest female persona
        voice_expr = "af_nicole*0.50 + af_sarah*0.35 + af_bella*0.15"

    if "+" not in voice_expr and "*" not in voice_expr and "-" not in voice_expr:
        try:
            style = kokoro.get_voice_style(voice_expr.strip())
            np.save(preset_file, style)
            return style
        except Exception:
            return voice_expr.strip()

    tokens = re.split(r'(\+|\-)', voice_expr)
    current_vector = None
    current_op = '+'

    for token in tokens:
        token = token.strip()
        if token in ('+', '-'):
            current_op = token
            continue
        if not token:
            continue

        if '*' in token:
            v_name, weight_str = token.split('*')
            weight = float(weight_str.strip())
            v_style = kokoro.get_voice_style(v_name.strip())
            vec = v_style * weight
        else:
            vec = kokoro.get_voice_style(token)

        if current_vector is None:
            current_vector = vec
        else:
            if current_op == '+':
                current_vector = current_vector + vec
            elif current_op == '-':
                current_vector = current_vector - vec

    if current_vector is not None:
        np.save(preset_file, current_vector)
        return current_vector

    return "am_adam"

def main():
    if len(sys.argv) < 2:
        print("Usage: python synth.py <text> [voice_algebra] [speed]")
        sys.exit(1)

    is_raw_pcm = "--raw-pcm" in sys.argv
    clean_argv = [a for a in sys.argv if a != "--raw-pcm"]

    voice_expr = clean_argv[2] if len(clean_argv) > 2 else "gideon"
    speed = float(clean_argv[3]) if len(clean_argv) > 3 else 1.0

    text = apply_lexicon_overrides(clean_argv[1], voice_expr)

    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    voice_payload = parse_voice_algebra(kokoro, voice_expr)

    audio, sr = kokoro.create(text, voice=voice_payload, speed=speed, lang="en-us")
    
    if is_raw_pcm:
        pcm_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        sys.stdout.buffer.write(pcm_int16.tobytes())
        sys.stdout.buffer.flush()
    else:
        out_dir = "C:/dev/speech-mcp-server/scratch"
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, f"out_{int(time.time()*1000)}.wav")
        sf.write(out_file, audio, sr)
        print(f"SYNTH_WAV:{out_file}")

if __name__ == "__main__":
    main()
