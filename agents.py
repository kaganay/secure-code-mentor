"""
agents.py — CrewAI ajanları (isimler hoca spesifikasyonu ile hizalı).

Neden LLM tek fabrika fonksiyonundan?
    Üç ajanın aynı model ailesini paylaşması maliyet ve davranış tutarlılığı sağlar;
    Yerel Ollama / Groq / OpenAI seçimi ortam değişkeniyle tek noktadan yönetilir (tek motor, üç ajan).

Neden iki farklı araç (Auditor: statik tarama, Professor: RAG)?
    "Mühendislik yaklaşımı" kriteri: yalnızca LLM çıkarımı yerine ölçülebilir araç çıktıları
    (deterministik tarama + literatür geri-getirme) raporda savunulabilir.
"""

from __future__ import annotations

import os

from crewai import Agent, LLM

from utils import run_static_security_scan, search_owasp_knowledge


def _provider_model_id(raw: str, provider: str) -> str:
    """
    CrewAI 1.x için sağlayıcı önekli model id (örn. openai/gpt-4o-mini, groq/llama-3.3-70b-versatile).

    .env'de sadece 'gpt-4o-mini' yazılmışsa openai/ eklenir; zaten 'openai/...' yazılmışsa dokunulmaz.
    """
    m = raw.strip()
    if "/" in m:
        return m
    return f"{provider}/{m}"


def _use_ollama() -> bool:
    """USE_OLLAMA=1 ile bulut API olmadan yerel inference (gizlilik / bağımsızlık)."""
    return os.getenv("USE_OLLAMA", "").lower() in ("1", "true", "yes")


def _build_llm() -> LLM:
    # 1) Yerel Ollama — dış API anahtarı gerekmez; ollama.com ile servis çalışır olmalı.
    if _use_ollama():
        raw = os.getenv("OLLAMA_MODEL", "llama3.2").strip()
        model = raw if raw.lower().startswith("ollama/") else f"ollama/{raw}"
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        return LLM(model=model, base_url=base)

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        raw = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        return LLM(
            model=_provider_model_id(raw, "groq"),
            api_key=groq_key,
        )
    raw = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return LLM(
        model=_provider_model_id(raw, "openai"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def build_security_auditor() -> Agent:
    """Security_Auditor: statik zafiyet sinyalleri + LLM sentezi."""
    return Agent(
        role="Security_Auditor",
        goal=(
            "Kodu OWASP Top 10 perspektifinden incele; önce run_static_security_scan aracını "
            "kod üzerinde kullan, ardından bulguları şablonla raporla."
        ),
        backstory=(
            "AppSec mühendisisin. Araç çıktısını (StaticScan) asla görmezden gelmezsin; "
            "LLM ile genişletir ve yanlış pozitifleri eleştirirsin."
        ),
        tools=[run_static_security_scan],
        verbose=True,
        llm=_build_llm(),
        allow_delegation=False,
    )


def build_cyber_security_professor() -> Agent:
    """Cyber_Security_Professor: neden-sonuç + saldırı senaryosu; OWASP aracı."""
    return Agent(
        role="Cyber_Security_Professor",
        goal=(
            "Auditor bulgularını akademik/pratik güvenlik diliyle açıkla; her bulgu için "
            "neden-sonuç zinciri ve gerçekçi saldırı senaryosu yaz. Gerekirse "
            "search_owasp_knowledge ile literatür pasajı çek."
        ),
        backstory=(
            "Üniversite düzeyi siber güvenlik profesörüsün. OWASP terminolojisini doğru "
            "kullanırsın; korku yerine mekanizma anlatırsın."
        ),
        tools=[search_owasp_knowledge],
        verbose=True,
        llm=_build_llm(),
        allow_delegation=False,
    )


def build_senior_refactor_engineer() -> Agent:
    """Senior_Refactor_Engineer: güvenli, modüler, performanslı refaktör."""
    return Agent(
        role="Senior_Refactor_Engineer",
        goal=(
            "Professor çıktısı ve özgün kod bağlamına dayanarak güvenli refaktör üret; "
            "davranışı gereksiz yere değiştirme; clean code ve güvenli varsayılanlar uygula."
        ),
        backstory=(
            "Staff-level yazılım mühendisisin. Threat modeling'i kod seviyesine indirirsin."
        ),
        tools=[],  # Neden boş? Refaktör çoğunlukla bağlam sentezidir; ileride AST/formatter aracı eklenebilir.
        verbose=True,
        llm=_build_llm(),
        allow_delegation=False,
    )
