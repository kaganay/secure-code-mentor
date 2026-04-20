# SecureCode Mentor

Freelance ve öğrenci geliştiriciler için **OWASP odaklı** çoklu ajan ([CrewAI](https://www.crewai.com/)) kod güvenliği mentoru: **anonimleştirme**, deterministik statik sinyaller, **RAG** ile OWASP literatürü, eğitimsel açıklama ve **güvenli refaktör** önerisi. Arayüz: **Streamlit** (`app.py`); otomasyon: **CLI** (`main.py`).

**GitHub:** [kaganay/secure-code-mentor](https://github.com/kaganay/secure-code-mentor)

---

## Özellikler

| Özellik | Açıklama |
|--------|----------|
| **Üç ajan, sıralı iş akışı** | `Security_Auditor` → `Cyber_Security_Professor` → `Senior_Refactor_Engineer` |
| **Gizlilik** | LLM’e gitmeden önce IP, e-posta, JWT, sabit sırlar vb. anonimleştirilir (`utils.anonymize_code_detailed`) |
| **Statik tarama** | `utils.static_security_scan_report`: SQLi/XSS/eval/shell=True/hardcoded secret desenleri — **denetim görevine otomatik enjekte** edilir |
| **RAG** | `knowledge/*.pdf` → Chroma; Professor `search_owasp_knowledge` ile sorgular |
| **Dashboard** | 1–100 skor, şiddet sayıları, kategori grafiği (model `**Severity:**` / `**Category:**` üretirse) |
| **Çıktı** | Sekmeler + tam Markdown indirme; ham tool-JSON kaçakları sonradan temizlenir |

---

## Mimari (dosyalar)

| Bileşen | Dosya |
|--------|--------|
| CLI | `main.py` |
| Streamlit UI | `app.py` |
| Ajan tanımları | `agents.py` |
| Görev zinciri (sequential) | `tasks.py` |
| Anonimleştirme, statik tarama, RAG, skor, crew çalıştırma | `utils.py` |

**Araçlar (güncel):**

- **Statik tarama:** Aynı motor (`static_security_scan_report`) görev açıklamasına yazılır; böylece yerel küçük modellerin rapora `{"name": "run_static_security_scan", ...}` gibi **sahte araç JSON’u** basması engellenir. Kodda `@tool run_static_security_scan` tanımı durur; pipeline özeti görevde verilir.
- **Professor:** `search_owasp_knowledge` — OWASP PDF pasajları.

**Çıktı temizliği:** `crew.kickoff()` sonrası `sanitize_llm_tool_dump_artifacts` kalan tool-JSON blob’larını ayıklar.

---

## Python sürümü (kurulum hatası)

`No matching distribution found for crewai...` ve listede yalnızca **0.1.x … 0.11.x** görünüyorsa büyük ihtimalle **Python 3.14+** veya **3.9−** kullanıyorsun. **CrewAI 1.x** şu an **`>=3.10,<3.14`** aralığında.

**Önerilen:** Python **3.12** veya **3.13** kur; venv’i **o yorumlayıcıyla** oluştur:

```powershell
cd C:\Users\kagan\Projects\secure-code-mentor
py -0
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python check_python_version.py
pip install -r requirements.txt
```

`py` yoksa kurulum yolunla örneğin:

`"C:\Program Files\Python312\python.exe" -m venv .venv`

### `Activate.ps1` sonrası hâlâ yanlış Python görünüyorsa

Venv yorumlayıcısını **doğrudan** kullan:

```powershell
cd C:\Users\kagan\Projects\secure-code-mentor
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe check_python_version.py
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Kurulum

1. Repoyu klonla, proje köküne gir:

   ```bash
   git clone https://github.com/kaganay/secure-code-mentor.git
   cd secure-code-mentor
   ```

2. Sanal ortam (kökta) ve bağımlılıklar:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Ortam değişkenleri:** `.env.example` dosyasını `.env` olarak kopyala ve doldur.

4. **OWASP PDF (isteğe bağlı):** `knowledge/` içine PDF ekle. İlk çalışmada Chroma kalıcı indeks `data/chroma/` altında oluşur.

---

## LLM seçimi (Ollama / Groq / OpenAI)

Üç ajan **aynı** LLM yapılandırmasını paylaşır (`agents.py` → `_build_llm`).

| Mod | `.env` | Not |
|-----|--------|-----|
| **Yerel Ollama** | `USE_OLLAMA=1`, isteğe bağlı `OLLAMA_MODEL=llama3.2`, `OLLAMA_BASE_URL=http://localhost:11434` | [ollama.com](https://ollama.com) + `ollama pull <model>`. API anahtarı gerekmez. |
| **Groq** | `GROQ_API_KEY=...` | `USE_OLLAMA` kapalı olmalı. |
| **OpenAI** | `OPENAI_API_KEY=...` | Öncelik sırası: Ollama → Groq → OpenAI. |

**Bellek:** Crew `memory=True` (varsayılan). Embedding / bellek hatasında `.env` içine `SECURECODE_DISABLE_MEMORY=1` ekle.

---

## Çalıştırma

**Streamlit (önerilen):**

```bash
streamlit run app.py
```

Tarayıcıda genelde **http://localhost:8501** — dış IP ile paylaşım ev ağında çalışmayabilir; yerel adres kullan.

**CLI:**

```bash
python main.py --file examples/insecure_sample.py
```

---

## Streamlit arayüzü (kısa tur)

- **Üst bölüm:** Başlık ve kısa açıklama; yan panelde LLM durumu ve mimari özeti.
- **Kod girişi:** Dosya yükle veya metin alanına yapıştır → **Analizi başlat**.
- **Özet:** Güvenlik skoru (1–100), kritik/orta/düşük sayıları, kategori çubuğu grafiği.
- **Sekmeler:** Auditor, Professor, Refactor, Ham rapor; **Tam raporu indir (.md)**.

Tema: `.streamlit/config.toml`.

---

## Demo kodu

`examples/insecure_sample.py` bilinçli zayıf örnekler içerir; arayüzde yükleyip veya içeriği yapıştırıp analiz edebilirsin.

---

## Sorun giderme

| Sorun | Öneri |
|--------|--------|
| `crewai` kurulmuyor | Python **3.10–3.13** + proje kökünde venv; `check_python_version.py` |
| Tarayıcı zaman aşımı | `localhost:8501` kullan; güvenlik duvarı / port yönlendirme kontrolü |
| Skor 100 / grafik boş | Küçük modeller bazen `**Severity:**` / `**Category:**` üretmez; **Ham rapor** sekmesine bak; statik blok yine görevde |
| Memory / embedding hatası | `SECURECODE_DISABLE_MEMORY=1` |
| Rapor bozuk JSON içeriyordu | Güncel sürümde görev enjekte + çıktı sanitization; `git pull` |

---

## Bağımlılıklar

`requirements.txt`: `crewai` 1.x, `streamlit`, `chromadb`, `openai`, `python-dotenv`, `pypdf`, `pandas`.

---

## Lisans

Ders / kişisel proje kullanımı; ihtiyaç halinde MIT veya benzeri lisans eklenebilir.
