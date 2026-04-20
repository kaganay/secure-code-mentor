"""
utils.py — yardımcı işlevler, RAG, raporlama ve Crew çalıştırma.

Neden tek dosyada toplandı?
    Hoca kriteri modülerliği dört dosya (main / agents / tasks / utils) ile sınırlıyor;
    bu dosya bilinçli olarak "çekirdek mühendislik katmanı"dır: anonimleştirme, statik tarama,
    RAG, metrik çıkarma ve pipeline tek yerde dokümante edilir (rapor için aranabilir).

Privacy vs. Memory (CrewAI memory=True):
    Hoca "Bellek (Memory)" mühendislik kriterini istiyor; bu nedenle Crew seviyesinde hafıza
    açık. Trade-off: oturum içi tutarlılık artar; üretimde PII içeren ham kodla memory=True
    önerilmez — burada kod LLM'e gitmeden önce anonimleştirilir ve bu tasarım kararı
    yorum satırlarıyla birlikte raporda tartışılabilir.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import chromadb
from chromadb.utils import embedding_functions
from crewai import Crew, Process
from crewai.tools import tool
from dotenv import load_dotenv
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# 1) Anonimleştirme (PII / sırlar)
# ---------------------------------------------------------------------------
# Neden regex?
#    LLM tabanlı maskeleme ek gecikme/gider ve tutarsızlık riski taşır; deterministik
#    kurallar hocanın istediği "teknik derinlik" için ölçülebilir ve tekrarlanabilir.


@dataclass(frozen=True)
class AnonymizeResult:
    text: str
    replacements: int


def anonymize_code(source: str) -> str:
    return anonymize_code_detailed(source).text


def anonymize_code_detailed(source: str) -> AnonymizeResult:
    text = source
    count = 0

    text, n = re.subn(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d{1,2})\b",
        "<REDACTED_IPv4>",
        text,
    )
    count += n

    text, n = re.subn(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "<REDACTED_EMAIL>",
        text,
        flags=re.IGNORECASE,
    )
    count += n

    text, n = re.subn(r"\bAKIA[0-9A-Z]{16}\b", "<REDACTED_AWS_ACCESS_KEY_ID>", text)
    count += n

    def _redact_secrets(m: re.Match[str]) -> str:
        return f"{m.group(1)}<REDACTED_SECRET>{m.group(3)}"

    text, n = re.subn(
        r'((?:api|secret|token|password|passwd|pwd|auth)\s*[=:]\s*["\'])([^\n"\']{8,})(["\'])',
        _redact_secrets,
        text,
        flags=re.IGNORECASE,
    )
    count += n

    text, n = re.subn(
        r"\bBearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\b",
        "Bearer <REDACTED_JWT>",
        text,
    )
    count += n

    return AnonymizeResult(text=text, replacements=count)


# ---------------------------------------------------------------------------
# 2) Statik kod tarama (Security_Auditor aracı)
# ---------------------------------------------------------------------------
# Neden ayrı bir araç?
#    Hoca "Araç Kullanımı" istiyor; tamamen LLM'e bırakılan tarama tekrarlanabilir değildir.
#    Bu fonksiyon kanıt üretir (desen eşleşmesi); LLM bulguları sentezler ve bağlamlar.


def static_security_scan_report(code: str) -> str:
    """Heuristik statik tarama — çıktı Markdown; ajanın görevine kanıt sağlar."""
    findings: list[str] = []
    c = code

    if re.search(r"execute\s*\(\s*[\"'].*%s.*[\"']", c, re.IGNORECASE):
        findings.append("- [SQLi riski] String birleştirme / % ile SQL execute benzeri desen.")
    if re.search(r"cursor\.execute\s*\(\s*f[\"']", c):
        findings.append("- [SQLi riski] f-string ile cursor.execute.")
    if re.search(r"(?:innerHTML|dangerouslySetInnerHTML)\s*=", c):
        findings.append("- [XSS riski] DOM innerHTML veya dangerouslySetInnerHTML ataması.")
    if re.search(r"pickle\.loads?\s*\(", c):
        findings.append("- [Deserialization] pickle.loads güvensiz kaynakla kullanılabilir.")
    if re.search(r"eval\s*\(", c):
        findings.append("- [Code injection] eval() kullanımı.")
    if re.search(r"subprocess\..*shell\s*=\s*True", c, re.IGNORECASE):
        findings.append("- [Command injection] subprocess shell=True.")
    if re.search(r"(?i)(?:api|secret|token|password)\s*=\s*[\"'][^\"'\n]{6,}[\"']", c):
        findings.append("- [Hardcoded secret] Sabit anahtar/şifre ataması olası.")

    if not findings:
        return "## StaticScan\nStatik desen taraması: belirgin bir anti-pattern bulunamadı.\n"
    return "## StaticScan (deterministik)\n" + "\n".join(findings) + "\n"


@tool("run_static_security_scan")
def run_static_security_scan(code_snippet: str) -> str:
    """
    Security_Auditor ajanının çağıracağı araç.
    Argüman: incelenecek kod (görev açıklamasındaki kodun tamamı veya özeti).
    """
    return static_security_scan_report(code_snippet or "")


# ---------------------------------------------------------------------------
# 3) RAG (OWASP PDF) + Professor aracı
# ---------------------------------------------------------------------------


def _chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _read_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


class OwaspKnowledgeBase:
    """Yerel PDF → Chroma. Kullanıcı kodu koleksiyona yazılmaz (yalnızca sorgu metni)."""

    def __init__(
        self,
        pdf_dir: str | Path = "knowledge",
        persist_dir: str | Path = "data/chroma",
        collection_name: str = "owasp_docs",
    ) -> None:
        self.pdf_dir = Path(pdf_dir)
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._ef = embedding_functions.DefaultEmbeddingFunction()
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._ef,
        )

    def sync_pdfs(self) -> int:
        if not self.pdf_dir.exists():
            self.pdf_dir.mkdir(parents=True, exist_ok=True)
            return 0

        pdf_paths = sorted(self.pdf_dir.glob("*.pdf"))
        if not pdf_paths:
            return 0

        documents: list[str] = []
        new_ids: list[str] = []
        metadatas: list[dict[str, str]] = []

        for pdf_path in pdf_paths:
            raw = _read_pdf_text(pdf_path)
            digest = hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()
            base_id = f"{pdf_path.name}:{digest[:12]}"
            for i, chunk in enumerate(_chunk_text(raw)):
                documents.append(chunk)
                new_ids.append(f"{base_id}:chunk:{i}")
                metadatas.append({"source": pdf_path.name, "chunk": str(i)})

        try:
            existing = self._collection.get()
            existing_ids = existing.get("ids") or []
            if existing_ids:
                self._collection.delete(ids=existing_ids)
        except Exception:
            pass

        if documents:
            self._collection.add(ids=new_ids, documents=documents, metadatas=metadatas)
        return len(documents)

    def query(self, text: str, n_results: int = 6) -> str:
        if not text.strip():
            return ""
        res = self._collection.query(query_texts=[text], n_results=n_results)
        docs: Iterable[str] = (res.get("documents") or [[]])[0] or []
        metas = (res.get("metadatas") or [[]])[0] or []
        blocks: list[str] = []
        for doc, meta in zip(docs, metas):
            src = meta.get("source", "unknown") if isinstance(meta, dict) else "unknown"
            blocks.append(f"[Kaynak: {src}]\n{doc}")
        return "\n\n---\n\n".join(blocks)


_kb: OwaspKnowledgeBase | None = None


def get_owasp_kb() -> OwaspKnowledgeBase:
    """Tekil KB: Professor aracı aynı indeksi paylaşır."""
    global _kb
    if _kb is None:
        _kb = OwaspKnowledgeBase()
    return _kb


@tool("search_owasp_knowledge")
def search_owasp_knowledge(search_query: str) -> str:
    """
    Cyber_Security_Professor'ün literatür destekli açıklama yapması için RAG aracı.
    Neden ayrı araç? Ajanın ihtiyaç duyduğu OWASP pasajını sorgu zamanında çekmesi
    (just-in-time retrieval) token israfını azaltabilir ve "tool use" kriterini kanıtlar.
    """
    kb = get_owasp_kb()
    kb.sync_pdfs()
    return kb.query(search_query or "OWASP Top 10 overview", n_results=5)


def build_rag_context_for_code(code: str) -> str:
    """Görev bağlamına önceden serpiştirilen OWASP özeti (Professor aracına ek)."""
    kb = get_owasp_kb()
    kb.sync_pdfs()
    head = code.strip().splitlines()[:40]
    head_txt = "\n".join(head)[:4000]
    query = (
        "OWASP Top 10: injection, access control, crypto failures, insecure design, "
        "misconfiguration, vulnerable components, auth failures, integrity, logging, SSRF.\n"
        f"Kod özeti:\n{head_txt}"
    )
    return kb.query(query, n_results=6)


# ---------------------------------------------------------------------------
# 4) Raporlama — Güvenlik skoru 1–100 (yüksek = daha güvenli) + kategoriler
# ---------------------------------------------------------------------------
# Neden ters skor?
#    Hoca "Güvenlik Skoru (1-100)" dediğinde tipik yorum: 100 mükemmel güvenlik.
#    Önceki "zafiyet skoru" (yüksek=kötü) raporda kafa karıştırır; burada tek tip ölçek.


_SEVERITY_RE = re.compile(
    r"\*\*Severity:\*\*\s*(Critical|Medium|Low)\b",
    flags=re.IGNORECASE,
)
_CATEGORY_RE = re.compile(
    r"\*\*Category:\*\*\s*(.+)$",
    flags=re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class SeverityCounts:
    critical: int
    medium: int
    low: int

    @property
    def total(self) -> int:
        return self.critical + self.medium + self.low


def count_severities(markdown_text: str) -> SeverityCounts:
    crit = med = low = 0
    for m in _SEVERITY_RE.finditer(markdown_text or ""):
        sev = m.group(1).lower()
        if sev == "critical":
            crit += 1
        elif sev == "medium":
            med += 1
        elif sev == "low":
            low += 1
    return SeverityCounts(critical=crit, medium=med, low=low)


def security_score_1_to_100(counts: SeverityCounts) -> int:
    """
    Bulgu sayısından güvenlik skoru: 100 en iyi, 1 en kötü (hocanın 1–100 aralığı).
    Ceza modeli lineer ve şeffaftır (raporda kalibre edilebilir).
    """
    penalty = counts.critical * 18 + counts.medium * 10 + counts.low * 4
    return max(1, min(100, 100 - penalty))


def extract_vulnerability_categories(markdown_text: str, limit: int = 12) -> dict[str, int]:
    """Dashboard için **Category:** satırlarından histogram."""
    cats: list[str] = []
    for m in _CATEGORY_RE.finditer(markdown_text or ""):
        label = m.group(1).strip()
        if label:
            cats.append(label[:80])
    return dict(Counter(cats).most_common(limit))


# Rapor başlıkları — `tasks.py` ile birebir aynı kalmalı (UI ayrıştırması).
_MARK_AUDITOR = "## Security_Auditor_Report"
_MARK_PROFESSOR = "## Cyber_Security_Professor_Report"
_MARK_ENGINEER = "## Refactored Code"


@dataclass(frozen=True)
class ReportSections:
    """Streamlit sekmeleri için birleşik crew çıktısını üç bölüme ayırır."""

    auditor: str
    professor: str
    engineer: str
    raw: str


def split_crew_report(raw_output: str) -> ReportSections:
    """
    CrewAI `kickoff()` genelde tek metin döndürür; kullanıcı deneyimi için bölümler ayrılır.

    Neden başlık tabanlı?
    JSON zorunluluğu bazı modellerde kırılgan; Markdown H2 başlıkları hem LLM hem insan için okunur.
    """
    text = (raw_output or "").strip()
    if not text:
        return ReportSections(auditor="", professor="", engineer="", raw="")

    prof_idx = text.find(_MARK_PROFESSOR)
    ref_idx = text.find(_MARK_ENGINEER)

    if prof_idx != -1:
        auditor = text[:prof_idx].strip()
        after_prof = text[prof_idx:]
        ref_rel = after_prof.find(_MARK_ENGINEER)
        if ref_rel != -1:
            professor = after_prof[:ref_rel].strip()
            engineer = after_prof[ref_rel:].strip()
        else:
            professor = after_prof.strip()
            engineer = ""
        return ReportSections(
            auditor=auditor or text,
            professor=professor,
            engineer=engineer,
            raw=raw_output,
        )

    if ref_idx != -1:
        return ReportSections(
            auditor=text[:ref_idx].strip(),
            professor="",
            engineer=text[ref_idx:].strip(),
            raw=raw_output,
        )

    return ReportSections(auditor=text, professor="", engineer="", raw=raw_output)


def markdown_for_metrics(sections: ReportSections) -> str:
    """Skor/kategori: çoğunlukla Auditor bulgularından; yoksa ham metin."""
    base = sections.auditor.strip()
    return base if base else sections.raw


def sanitize_llm_tool_dump_artifacts(text: str) -> str:
    """
    Yerel / zayıf modeller bazen araç çağrısını metne `{"name": "...", "parameters": ...}` olarak basar.
    Bu, raporu kirletir; dengeli süslü parantez taramasıyla blob'ları çıkarır.
    """
    s = text or ""
    tool_names = ("run_static_security_scan", "search_owasp_knowledge")
    for _ in range(80):
        removed = False
        for tool in tool_names:
            m = re.search(rf'\{{\s*"name"\s*:\s*"{re.escape(tool)}"', s)
            if not m:
                continue
            start = m.start()
            depth = 0
            end = -1
            for j in range(start, len(s)):
                ch = s[j]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = j + 1
                        break
            if end == -1:
                s = s[:start] + s[m.end() :]
            else:
                k = end
                while k < len(s) and s[k] in " \t\n\r;":
                    k += 1
                s = s[:start] + s[k:]
            removed = True
            break
        if not removed:
            break
    s = re.sub(r"\n{5,}", "\n\n\n\n", s)
    return s.strip()


# ---------------------------------------------------------------------------
# 5) Crew çalıştırma
# ---------------------------------------------------------------------------


def run_crew_on_code(code: str, rag_context: str) -> str:
    """agents/tasks import döngüsünü önlemek için burada gecikmeli import."""
    load_dotenv()
    from agents import (
        build_cyber_security_professor,
        build_security_auditor,
        build_senior_refactor_engineer,
    )
    from tasks import build_tasks

    auditor = build_security_auditor()
    professor = build_cyber_security_professor()
    engineer = build_senior_refactor_engineer()

    tasks = build_tasks(
        code=code,
        rag_context=rag_context,
        auditor=auditor,
        professor=professor,
        refactor_engineer=engineer,
    )

    # Varsayılan memory=True (hoca kriteri). Embedding/API sorunu yaşanırsa SECURECODE_DISABLE_MEMORY=1.
    memory_on = os.getenv("SECURECODE_DISABLE_MEMORY", "").lower() not in ("1", "true", "yes")
    crew = Crew(
        agents=[auditor, professor, engineer],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=memory_on,
    )
    result = crew.kickoff()
    return sanitize_llm_tool_dump_artifacts(str(result))
