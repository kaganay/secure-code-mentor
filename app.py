"""
app.py — Streamlit profesyonel MVP dashboard.

Neden Streamlit?
    Hızlı görselleştirme + dosya yükleme; ders projesi için "çalışan ürün" hissi verir.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from utils import (
    anonymize_code_detailed,
    build_rag_context_for_code,
    count_severities,
    extract_vulnerability_categories,
    run_crew_on_code,
    security_score_1_to_100,
)


def main() -> None:
    load_dotenv()

    st.set_page_config(page_title="SecureCode Mentor", layout="wide")
    st.title("SecureCode Mentor")
    st.caption("Multi-Agent (CrewAI) · OWASP odaklı kod güvenliği mentoru")

    with st.sidebar:
        st.subheader("Mühendislik notları")
        st.markdown(
            "- **Sequential workflow:** Auditor → Professor → Engineer (`tasks.py`).\n"
            "- **Tools:** Statik tarama + OWASP RAG (`utils.py`).\n"
            "- **Memory:** Crew `memory=True` (raporda trade-off anlatımı için `utils.py`).\n"
            "- **Anonimleştirme:** LLM öncesi PII/sır maskeleme.\n"
        )
        st.divider()
        st.subheader("API anahtarları")
        if os.getenv("GROQ_API_KEY"):
            st.success("Groq algılandı.")
        elif os.getenv("OPENAI_API_KEY"):
            st.success("OpenAI algılandı.")
        else:
            st.error("OPENAI_API_KEY veya GROQ_API_KEY gerekli.")

    uploaded = st.file_uploader("Kaynak dosya yükle", type=None)
    pasted = st.text_area("Kodu yapıştır", height=280, placeholder="# güvenlik açısından tartışmalı örnek kod...")

    raw = ""
    if uploaded is not None:
        raw = uploaded.getvalue().decode("utf-8", errors="replace")
    elif pasted.strip():
        raw = pasted

    if st.button("Analizi başlat", type="primary", disabled=not raw.strip()):
        detailed = anonymize_code_detailed(raw)
        st.info(f"Anonimleştirme uygulandı ({detailed.replacements} değişiklik).")

        with st.spinner("RAG senkronu ve ajan zinciri çalışıyor (sequential + memory)..."):
            rag_context = build_rag_context_for_code(detailed.text)
            output = run_crew_on_code(code=detailed.text, rag_context=rag_context)

        counts = count_severities(output)
        score = security_score_1_to_100(counts)
        cats = extract_vulnerability_categories(output)

        st.subheader("Analiz özeti")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Güvenlik skoru (1–100)", score)
        c2.metric("Kritik bulgu", counts.critical)
        c3.metric("Orta", counts.medium)
        c4.metric("Düşük", counts.low)

        if cats:
            st.subheader("Zafiyet kategorileri (histogram)")
            df = pd.DataFrame(
                [{"Kategori": k, "Adet": v} for k, v in cats.items()],
            )
            st.bar_chart(df.set_index("Kategori"))
        else:
            st.caption("Kategori histogramı için LLM çıktısında **Category:** satırları beklenir.")

        st.divider()
        st.subheader("Tam rapor (ajan çıktıları)")
        st.markdown(output)


if __name__ == "__main__":
    main()
