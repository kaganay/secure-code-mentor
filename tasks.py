"""
tasks.py — sıralı (sequential) çok adımlı iş akışı.

Neden context=[önceki_task]?
    CrewAI'de context zinciri Auditor → Professor → Engineer sırasını garanti eder;
    böylece Professor yalnızca kendi hayal gücüyle değil, önceki görevin çıktısıyla çalışır
    (hocanın "hatalı cevapları düzeltme" senaryosunda savunulabilir mimari).
"""

from __future__ import annotations

from crewai import Agent, Task


def build_tasks(
    code: str,
    rag_context: str,
    auditor: Agent,
    professor: Agent,
    refactor_engineer: Agent,
) -> list[Task]:
    audit_task = Task(
        description=(
            "1) Önce `run_static_security_scan` aracını çağır; argüman olarak aşağıdaki kodun "
            "TAMAMINI ver.\n"
            "2) Aracın çıktısını ve kodu birlikte değerlendir; OWASP Top 10'a göre ek bulgular ekle.\n"
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
