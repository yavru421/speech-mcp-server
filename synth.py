import sys
import os
import re
import time
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

MODEL_PATH = "C:/dev/kokoro-v0_19.onnx"
VOICES_PATH = "C:/dev/voices.bin"
PRESETS_DIR = "C:/dev/speech-mcp-server/presets"

LEXICON_OVERRIDES = {
    "duckdb": "duck DB",
    "wasapi": "Wah-sah-pee",
    "onnx": "Onix",
    "dpapi": "D P A P I",
    "metropolis": "Meh-trop-oh-lis",
    "yeah": "yah",
    "bag": "bayg",
    "bags": "baygz",
    "roof": "ruff",
    "creek": "crick",
    "ope": "oh-pe",
    "wisconsin": "Wih-scon-sin",
    "bubbler": "buhb-ler",
    "suppose": "s'pose",
    "know what i mean": "know'm'sayin",
    "know what im saying": "know'm'sayin",
    "know what i'm saying": "know'm'sayin"
}

def apply_lexicon_overrides(text):
    words = text.split()
    processed = []
    for w in words:
        clean = re.sub(r'[^\w\s]', '', w).lower()
        if clean in LEXICON_OVERRIDES:
            processed.append(LEXICON_OVERRIDES[clean])
        else:
            processed.append(w)
    return " ".join(processed)

def parse_voice_algebra(kokoro, voice_expr):
    """
    Parses voice vector algebra expressions like:
    - 'am_adam'
    - 'af_bella*0.7 + am_adam*0.3'
    - 'am_adam+am_michael'
    """
    os.makedirs(PRESETS_DIR, exist_ok=True)
    
    preset_file = os.path.join(PRESETS_DIR, f"{voice_expr}.npy")
    if os.path.exists(preset_file):
        return np.load(preset_file)

    if "+" not in voice_expr and "*" not in voice_expr and "-" not in voice_expr:
        try:
            return kokoro.get_voice_style(voice_expr.strip())
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

    return current_vector if current_vector is not None else "am_adam"

def main():
    if len(sys.argv) < 2:
        print("Usage: python synth.py <text> [voice_algebra] [speed]")
        sys.exit(1)

    text = apply_lexicon_overrides(sys.argv[1])
    voice_expr = sys.argv[2] if len(sys.argv) > 2 else "am_adam*0.65 + bm_lewis*0.30 + am_michael*0.05"
    speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0

    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    voice_payload = parse_voice_algebra(kokoro, voice_expr)

    audio, sr = kokoro.create(text, voice=voice_payload, speed=speed, lang="en-us")
    
    out_dir = "C:/dev/speech-mcp-server/scratch"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"out_{int(time.time()*1000)}.wav")
    
    sf.write(out_file, audio, sr)
    print(f"SYNTH_WAV:{out_file}")

if __name__ == "__main__":
    main()
