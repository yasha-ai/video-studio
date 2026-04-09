#!/usr/bin/env python3
"""Run description generation in subprocess to avoid blocking UI.

Usage: python description_subprocess.py <transcript_file> <title> [count]
Outputs JSON with descriptions to stdout.
"""
import sys
import json


def main():
    transcript_file = sys.argv[1]
    title = sys.argv[2]
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 9

    with open(transcript_file, "r", encoding="utf-8") as f:
        transcript = f.read()

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))
    from src.processors.description_generator import DescriptionGenerator

    gen = DescriptionGenerator()
    descriptions = gen.generate_descriptions(
        transcript=transcript,
        title=title,
        count=count,
    )

    print(json.dumps({
        "descriptions": descriptions,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
