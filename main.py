"""
main.py — CLI giriş noktası.

Neden CLI ayrı?
    Streamlit olmayan ortamlarda (CI, ssh) aynı pipeline çalıştırılabilir;
    hoca "teknik derinlik" için hem UI hem otomasyon yolu gösterilir.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from utils import (
    anonymize_code_detailed,
    build_rag_context_for_code,
    count_severities,
    extract_vulnerability_categories,
    markdown_for_metrics,
    run_crew_on_code,
    security_score_1_to_100,
    split_crew_report,
)


def _read_input(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    return sys.stdin.read()


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="SecureCode Mentor (CrewAI) CLI")
    parser.add_argument(
        "--file",
        "-f",
        help="İncellenecek kaynak dosya yolu (verilmezse stdin okunur)",
        default=None,
    )
    args = parser.parse_args()

    source = _read_input(args.file)
    if not source.strip():
        print("Boş girdi: dosya veya stdin ile kod sağlayın.", file=sys.stderr)
        return 2

    detailed = anonymize_code_detailed(source)
    print(f"[privacy] anonimleştirme değişikliği: {detailed.replacements}", file=sys.stderr)

    rag_context = build_rag_context_for_code(detailed.text)
    output = run_crew_on_code(code=detailed.text, rag_context=rag_context)

    sections = split_crew_report(output)
    metrics_md = markdown_for_metrics(sections)
    counts = count_severities(metrics_md)
    score = security_score_1_to_100(counts)
    cats = extract_vulnerability_categories(metrics_md)
    print(
        f"[report] güvenlik_skoru(1-100)={score} "
        f"kritik={counts.critical} orta={counts.medium} düşük={counts.low} "
        f"kategoriler={cats}",
        file=sys.stderr,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
