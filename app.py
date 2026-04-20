"""
SecureCode Mentor — Streamlit arayüzü (özet dashboard + ajan sekmeleri + rapor indirme).
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
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&display=swap" rel="stylesheet">
        <style>
            html, body, [class*="css"]  {
                font-family: 'DM Sans', ui-sans-serif, system-ui, sans-serif !important;
            }
            .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1200px; }
            h1 { letter-spacing: -0.02em; font-weight: 700 !important; }
            .scm-hero {
                background: linear-gradient(135deg, #0f766e 0%, #0d9488 45%, #14b8a6 100%);
                color: #ecfeff;
                padding: 1.35rem 1.5rem;
                border-radius: 12px;
                margin-bottom: 1.25rem;
                box-shadow: 0 10px 40px -12px rgba(13, 148, 136, 0.45);
            }
            .scm-hero h2 { margin: 0; font-size: 1.35rem; font-weight: 700; color: #f0fdfa !important; }
            .scm-hero p { margin: 0.45rem 0 0 0; opacity: 0.92; font-size: 0.95rem; }
            div[data-testid="stMetric"] {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                padding: 14px 16px;
                border-radius: 10px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }
            div[data-testid="stMetric"] label { color: #64748b !important; font-size: 0.8rem !important; }
            div[data-testid="stMetric"] [data-testid="stMetricValue"] {
                color: #0f172a !important; font-weight: 700 !important;
            }
            [data-testid="stTabs"] button { font-weight: 600; }
            .scm-card-title { font-size: 0.95rem; font-weight: 600; color: #0f172a; margin-bottom: 0.5rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _llm_status_message() -> tuple[str, str]:
    if os.getenv("USE_OLLAMA", "").lower() in ("1", "true", "yes"):
        return "ok", "Yerel Ollama (`USE_OLLAMA=1`) — API anahtarı gerekmez."
    if os.getenv("GROQ_API_KEY"):
        return "ok", "Groq API algılandı."
    if os.getenv("OPENAI_API_KEY"):
        return "ok", "OpenAI API algılandı."
    return "err", "`.env` içinde `USE_OLLAMA=1` veya Groq / OpenAI anahtarı gerekli."


def main() -> None:
    st.set_page_config(
        page_title="SecureCode Mentor",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    load_dotenv()
    _inject_page_style()

    st.markdown(
        """
        <div class="scm-hero">
            <h2>SecureCode Mentor</h2>
            <p>Çoklu ajan (CrewAI) ile OWASP odaklı kod denetimi, eğitim ve güvenli refaktör önerisi.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown('<p class="scm-card-title">Durum</p>', unsafe_allow_html=True)
        kind, msg = _llm_status_message()
        if kind == "ok":
            st.success(msg)
        else:
            st.error(msg)

        with st.expander("Mimari özeti", expanded=False):
            st.markdown(
                "- **Sıra:** Security_Auditor → Cyber_Security_Professor → Senior_Refactor_Engineer\n"
                "- **Araçlar:** Statik tarama + OWASP RAG (`utils.py`)\n"
                "- **Memory:** `memory=True` — sorun olursa `SECURECODE_DISABLE_MEMORY=1`\n"
                "- **Örnek:** `examples/insecure_sample.py`\n"
            )
        st.divider()
        st.caption("[GitHub: kaganay/secure-code-mentor](https://github.com/kaganay/secure-code-mentor)")

    left, right = st.columns([1.55, 1], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<p class="scm-card-title">Kod girişi</p>', unsafe_allow_html=True)
            uploaded = st.file_uploader(
                "Dosya yükle",
                type=None,
                help="Herhangi bir metin kaynak dosyası; yoksa aşağıya yapıştır.",
                label_visibility="collapsed",
            )
            pasted = st.text_area(
                "Kaynak kod",
                height=280,
                placeholder="# Örnek: examples/insecure_sample.py\n# veya kendi bilerek zayıf bıraktığın kısa kod parçan…",
                label_visibility="collapsed",
            )

    with right:
        with st.container(border=True):
            st.markdown('<p class="scm-card-title">Hızlı ipuçları</p>', unsafe_allow_html=True)
            st.markdown(
                "- Yerel **Ollama** yavaş olabilir; ilk analiz **birkaç dakika** sürebilir.\n"
                "- Özet skoru, model `**Severity:**` satırlarını üretirse anlamlı olur.\n"
                "- Sonuçları **sekmelerden** ve **Ham rapor**dan kontrol et.\n"
            )

    raw = ""
    if uploaded is not None:
        raw = uploaded.getvalue().decode("utf-8", errors="replace")
    elif pasted.strip():
        raw = pasted

    st.markdown("")
    run = st.button(
        "Analizi başlat",
        type="primary",
        disabled=not raw.strip(),
        use_container_width=True,
    )

    if not raw.strip() and not run:
        st.info("Başlamak için sol taraftan dosya seç veya kodu yapıştır, ardından **Analizi başlat**.")

    if run:
        detailed = anonymize_code_detailed(raw)
        st.info(f"Gizlilik: LLM öncesi **{detailed.replacements}** anonimleştirme uygulandı.")

        with st.spinner("RAG senkronu ve ajan zinciri çalışıyor (Auditor → Professor → Engineer)…"):
            rag_context = build_rag_context_for_code(detailed.text)
            output = run_crew_on_code(code=detailed.text, rag_context=rag_context)

        sections = split_crew_report(output)
        metrics_md = markdown_for_metrics(sections)
        counts = count_severities(metrics_md)
        score = security_score_1_to_100(counts)
        cats = extract_vulnerability_categories(metrics_md)

        st.success("Analiz tamamlandı. Aşağıda özet ve ajan çıktıları.")
        st.markdown("### Özet dashboard")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Güvenlik skoru (1–100)", score, help="100 en iyi; bulgulara göre ceza düşer.")
        c2.metric("Kritik", counts.critical)
        c3.metric("Orta", counts.medium)
        c4.metric("Düşük", counts.low)

        if cats:
            st.markdown("#### Zafiyet kategorileri")
            df = pd.DataFrame([{"Kategori": k, "Adet": v} for k, v in cats.items()])
            st.bar_chart(df.set_index("Kategori"), height=280)
        else:
            st.caption(
                "Kategori grafiği için Auditor çıktısında `**Category:**` satırları gerekir; "
                "yerel model şablonu bozduysa grafik boş kalabilir — **Ham rapor** sekmesine bak."
            )

        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        st.download_button(
            label="Tam raporu indir (.md)",
            data=output.encode("utf-8"),
            file_name=f"securecode-mentor-rapor-{ts}.md",
            mime="text/markdown",
            type="secondary",
            use_container_width=True,
        )

        st.divider()
        st.markdown("### Ajan çıktıları")
        tab_a, tab_p, tab_e, tab_raw = st.tabs(
            [
                "Auditor",
                "Professor",
                "Refactor",
                "Ham rapor",
            ],
        )
        with tab_a:
            st.markdown(
                sections.auditor
                or "_Bu sekme için `## Security_Auditor_Report` veya önceki bölüm bulunamadı._"
            )
        with tab_p:
            st.markdown(
                sections.professor
                or "_`## Cyber_Security_Professor_Report` başlığı ayırt edilemedi._"
            )
        with tab_e:
            st.markdown(
                sections.engineer or "_`## Refactored Code` başlığı ayırt edilemedi._"
            )
        with tab_raw:
            st.markdown(output)


if __name__ == "__main__":
    main()
