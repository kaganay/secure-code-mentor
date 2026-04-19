"""
agents.py — CrewAI ajanları (isimler hoca spesifikasyonu ile hizalı).

Neden LLM tek fabrika fonksiyonundan?
    Üç ajanın aynı model ailesini paylaşması maliyet ve davranış tutarlılığı sağlar;
    Groq/OpenAI seçimi ortam değişkeniyle tek noktadan yönetilir.

Neden iki farklı araç (Auditor: statik tarama, Professor: RAG)?
    "Mühendislik yaklaşımı" kriteri: yalnızca LLM çıkarımı yerine ölçülebilir araç çıktıları
    (deterministik tarama + literatür geri-getirme) raporda savunulabilir.
"""

from __future__ import annotations

import os

from crewai import Agent, LLM

from utils import run_static_security_scan, search_owasp_knowledge


def _build_llm() -> LLM:
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        return LLM(
            model=os.getenv("GROQ_MODEL", "groq/llama-3.3-70b-versatile"),
            api_key=groq_key,
        )
    return LLM(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
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
