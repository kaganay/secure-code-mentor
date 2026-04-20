"""
tasks.py — sıralı (sequential) çok adımlı iş akışı.

Neden context=[önceki_task]?
    CrewAI'de context zinciri Auditor → Professor → Engineer sırasını garanti eder;
    böylece Professor yalnızca kendi hayal gücüyle değil, önceki görevin çıktısıyla çalışır
    (hocanın "hatalı cevapları düzeltme" senaryosunda savunulabilir mimari).
"""

from __future__ import annotations

from crewai import Agent, Task

from utils import static_security_scan_report


def build_tasks(
    code: str,
    rag_context: str,
    auditor: Agent,
    professor: Agent,
    refactor_engineer: Agent,
) -> list[Task]:
    static_block = static_security_scan_report(code)

    audit_task = Task(
        description=(
            "Çıktının en üstüne mutlaka şu başlığı koy (UI sekmeleri bununla ayrıştırır):\n"
            "## Security_Auditor_Report\n\n"
            "Aşağıdaki blok, `utils.static_security_scan_report` ile üretilmiş **deterministik** "
            "statik taramadır (Crew aracı değil — tekrar JSON veya `run_static_security_scan` "
            "çağrısı yazma).\n\n"
            f"{static_block}\n"
            "Bu çıktıyı ve aşağıdaki kodu birlikte değerlendir; OWASP Top 10'a göre ek bulgular ekle.\n"
            "Raporunda asla `{\"name\":` veya `parameters` içeren araç çağrısı formatı kullanma.\n\n"
            "Her bulgu için ŞU FORMATI aynen kullan:\n"
            "### Finding <n>\n"
            "**Severity:** Critical|Medium|Low\n"
            "**Category:** <kısa başlık>\n"
            "**Evidence:** <kod satırı/parçası veya gösterge>\n"
            "**Why it matters:** <teknik gerekçe>\n\n"
            "Ön-bağlam (RAG özeti, ek referans):\n"
            f"{rag_context}\n\n"
            "İncellenecek kod:\n"
            f"{code}\n"
        ),
        expected_output="Markdown: bulgular listesi (şablon).",
        agent=auditor,
    )

    professor_task = Task(
        description=(
            "Önceki görevin (Security_Auditor) Markdown çıktısını esas al.\n"
            "Her bulgu için:\n"
            "- Neden tehlikeli? (neden-sonuç)\n"
            "- Siber saldırı senaryosu (adım adım)\n"
            "- Savunma / sertleştirme önerisi\n"
            "Gerekirse `search_owasp_knowledge` ile ilgili OWASP pasajlarını getir.\n"
            "Çıktı başlığı: ## Cyber_Security_Professor_Report\n"
        ),
        expected_output="Markdown: eğitim ve tehdit modeli raporu.",
        agent=professor,
        context=[audit_task],
    )

    refactor_task = Task(
        description=(
            "Auditor bulguları ve Professor raporunu kullanarak kodu güvenli biçimde yeniden yaz.\n"
            "## Refactored Code\n"
            "```\n<kod>\n```\n"
            "## Change Summary\n"
            "- ...\n"
        ),
        expected_output="Markdown: refaktör + özet.",
        agent=refactor_engineer,
        context=[audit_task, professor_task],
    )

    return [audit_task, professor_task, refactor_task]
