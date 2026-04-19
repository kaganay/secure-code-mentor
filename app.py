"""
SecureCode Mentor — Streamlit arayüzü (özet dashboard + ajan sekmeleri + rapor indirme).

Rapor / hoca kriterleriyle hizalama:
    Kod yükleme veya yapıştırma, 1–100 güvenlik skoru, şiddet metrikleri, kategori grafiği,
    üç ajanın çıktılarının ayrı sekmelerde gösterimi, tam Markdown indirme.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
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


def _inject_page_style() -> None:
    """Streamlit varsayılanını biraz sıkılaştırır (rapor ekranı için)."""
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; }
        div[data-testid="stMetric"] { background: var(--secondary-background-color);
            padding: 12px 16px; border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    load_dotenv()
    _inject_page_style()

    st.set_page_config(page_title="SecureCode Mentor", layout="wide")
    st.title("SecureCode Mentor")
    st.caption("Multi-Agent (CrewAI) · OWASP odaklı kod güvenliği mentoru")

    with st.sidebar:
        st.subheader("Mimari özeti")
        st.markdown(
            "- **Sıra:** Security_Auditor → Cyber_Security_Professor → Senior_Refactor_Engineer\n"
            "- **Araçlar:** Statik tarama + OWASP RAG (`utils.py`)\n"
            "- **Memory:** Crew `memory=True` (sorun olursa `SECURECODE_DISABLE_MEMORY=1`)\n"
            "- **Örnek zayıf kod:** `examples/insecure_sample.py`\n"
        )
        st.divider()
        st.subheader("API anahtarları")
        if os.getenv("GROQ_API_KEY"):
            st.success("Groq algılandı.")
        elif os.getenv("OPENAI_API_KEY"):
            st.success("OpenAI algılandı.")
        else:
            st.error("`.env` içinde OPENAI_API_KEY veya GROQ_API_KEY gerekli.")

        st.divider()
        st.caption(
            "Repo: [github.com/kaganay/secure-code-mentor](https://github.com/kaganay/secure-code-mentor)"
        )

    uploaded = st.file_uploader("Kaynak dosya yükle", type=None)
    pasted = st.text_area("Ya da kodu yapıştırın", height=260, placeholder="# Örnek: examples/insecure_sample.py içeriğini buraya alın…")

    raw = ""
    if uploaded is not None:
        raw = uploaded.getvalue().decode("utf-8", errors="replace")
    elif pasted.strip():
        raw = pasted

    if st.button("Analizi başlat", type="primary", disabled=not raw.strip()):
        detailed = anonymize_code_detailed(raw)
        st.info(f"Anonimleştirme: {detailed.replacements} değişiklik uygulandı (LLM öncesi).")

        with st.spinner("RAG senkronu ve ajan zinciri çalışıyor…"):
            rag_context = build_rag_context_for_code(detailed.text)
            output = run_crew_on_code(code=detailed.text, rag_context=rag_context)

        sections = split_crew_report(output)
        metrics_md = markdown_for_metrics(sections)
        counts = count_severities(metrics_md)
        score = security_score_1_to_100(counts)
        cats = extract_vulnerability_categories(metrics_md)

        st.subheader("Özet dashboard")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Güvenlik skoru (1–100)", score)
        c2.metric("Kritik", counts.critical)
        c3.metric("Orta", counts.medium)
        c4.metric("Düşük", counts.low)

        if cats:
            st.markdown("**Zafiyet kategorileri**")
            df = pd.DataFrame([{"Kategori": k, "Adet": v} for k, v in cats.items()])
            st.bar_chart(df.set_index("Kategori"))
        else:
            st.caption(
                "Kategori grafiği için Auditor çıktısında `**Category:**` satırları gerekir; "
                "model şablonu bozduysa grafik boş kalabilir."
            )

        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        st.download_button(
            label="Tam raporu indir (.md)",
            data=output.encode("utf-8"),
            file_name=f"securecode-mentor-rapor-{ts}.md",
            mime="text/markdown",
        )

        st.divider()
        st.subheader("Ajan çıktıları")
        tab_a, tab_p, tab_e, tab_raw = st.tabs(
            [
                "Security_Auditor",
                "Cyber_Security_Professor",
                "Senior_Refactor_Engineer",
                "Ham rapor",
            ],
        )
        with tab_a:
            st.markdown(sections.auditor or "_Bu sekme için `## Security_Auditor_Report` / önceki bölüm bulunamadı._")
        with tab_p:
            st.markdown(
                sections.professor
                or "_Professor bölümü ayırt edilemedi; model `## Cyber_Security_Professor_Report` başlığını kullanmalı._"
            )
        with tab_e:
            st.markdown(
                sections.engineer
                or "_Refaktör bölümü ayırt edilemedi; model `## Refactored Code` başlığını kullanmalı._"
            )
        with tab_raw:
            st.markdown(output)


if __name__ == "__main__":
    main()
