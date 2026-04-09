#!/usr/bin/env python3
"""Run Whisper transcription in a subprocess to avoid GIL blocking the UI.

Usage: python -m src.processors.whisper_subprocess <wav_path> [model] [device]
Outputs SRT text to stdout.
"""

import sys
import os


def main():
    if len(sys.argv) < 2:
        print("Usage: whisper_subprocess.py <wav_path> [model] [device]", file=sys.stderr)
        sys.exit(1)

    wav_path = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else os.getenv("WHISPER_MODEL", "base")
    device = sys.argv[3] if len(sys.argv) > 3 else os.getenv("WHISPER_DEVICE", "cpu")

    # Patch SSL for macOS
    import ssl
    try:
        import certifi
        ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ssl._create_default_https_context = ssl._create_unverified_context

    import whisper

    model = whisper.load_model(model_name, device=device)
    result = model.transcribe(wav_path, language="ru")

    # Output as SRT-like text
    text = result.get("text", "")
    segments = result.get("segments", [])

    if segments:
        # Build SRT format
        for i, seg in enumerate(segments, 1):
            start = seg["start"]
            end = seg["end"]
            txt = seg["text"].strip()
            sh, sm, ss = int(start // 3600), int((start % 3600) // 60), start % 60
            eh, em, es = int(end // 3600), int((end % 3600) // 60), end % 60
            print(f"{i}")
            print(f"{sh:02d}:{sm:02d}:{ss:06.3f}".replace(".", ",") +
                  f" --> " +
                  f"{eh:02d}:{em:02d}:{es:06.3f}".replace(".", ","))
            print(txt)
            print()
    else:
        print(text)


if __name__ == "__main__":
    main()
