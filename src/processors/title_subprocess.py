#!/usr/bin/env python3
"""Run title generation + critique in subprocess to avoid blocking UI.

Usage: python title_subprocess.py <transcript_file> [count] [max_iterations] [quality_threshold]
Outputs JSON with titles and critiques to stdout.
"""
import sys
import json
import os


def main():
    transcript_file = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 9
    max_iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    quality_threshold = int(sys.argv[4]) if len(sys.argv) > 4 else 90

    with open(transcript_file, "r", encoding="utf-8") as f:
        transcript = f.read()

    # Import here so module loading happens in subprocess
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))
    from src.processors.title_generator import TitleGenerator

    gen = TitleGenerator()
    best_titles = []
    best_critiques = {}
    best_score = 0

    for iteration in range(1, max_iterations + 1):
        print(json.dumps({"progress": f"Генерация заголовков (попытка {iteration}/{max_iterations})..."}),
              flush=True)

        titles = gen.generate_titles(transcript=transcript, count=count, style="engaging")
        titles = [t.replace("<", "(").replace(">", ")") for t in titles]

        critiques = {}
        for t in titles:
            try:
                critiques[t] = gen.critique_title(t, transcript=transcript)
            except Exception:
                pass

        top_score = max((c.get("score", 0) for c in critiques.values()), default=0)

        if top_score > best_score:
            best_titles = titles
            best_critiques = critiques
            best_score = top_score

        if top_score >= quality_threshold:
            break

    # Output final result as JSON
    print(json.dumps({
        "result": True,
        "titles": best_titles,
        "critiques": {k: v for k, v in best_critiques.items()},
        "best_score": best_score,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
