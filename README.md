# SecureCode Mentor

Freelance ve öğrenci geliştiriciler için **OWASP odaklı** çoklu ajan (CrewAI) kod güvenliği mentoru: statik sinyaller, RAG ile literatür desteği, eğitimsel açıklama ve güvenli refaktör önerisi.

**GitHub:** [kaganay/secure-code-mentor](https://github.com/kaganay/secure-code-mentor)

## Önemli: Python sürümü (kurulum hatası alıyorsan)

`pip install` şuna benzer bir hata veriyorsa:

`No matching distribution found for crewai...` ve listede yalnızca **0.1.x … 0.11.x** görünüyorsa, büyük ihtimalle **Python 3.14 veya üzeri** (veya **3.9 ve altı**) kullanıyorsun. **CrewAI 1.x** PyPI’da şu an **`>=3.10,<3.14`** ile sınırlı; bu aralığın dışında pip uygun tekerlek bulamaz.

**Yapman gereken:** [python.org](https://www.python.org/downloads/) üzerinden **Python 3.12 veya 3.13** kur. Sonra venv’i **o sürümle** oluştur:

```powershell
cd C:\Users\kagan\Projects\secure-code-mentor
py -0
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python check_python_version.py
pip install -r requirements.txt
```

`py -0` yüklü Pythonları listeler; `-3.12` yoksa kurduğun sürüme göre `-3.13` dene. `py` yoksa, kurulumdan gelen tam yol ile örneğin `"C:\Program Files\Python312\python.exe" -m venv .venv` kullan.

### `Activate.ps1` sonrası hâlâ Python 3.14 / pip 3.14 görünüyorsa

Windows’ta `python` veya `pip` bazen **global 3.14**’e gider (`AppData\Local\Python\pythoncore-3.14-64\...`). Sanal ortamı şu komutlarla **zorla** kullan:

```powershell
cd C:\Users\kagan\Projects\secure-code-mentor
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe check_python_version.py
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`python --version` yerine mutlaka `.\.venv\Scripts\python.exe --version` ile doğrula (3.12.x görmelisin).

## Mimari (özet)

| Bileşen | Dosya |
|--------|--------|
| CLI | `main.py` |
| Streamlit UI | `app.py` |
| Ajanlar | `agents.py` |
| Görev zinciri (sequential) | `tasks.py` |
| Anonimleştirme, araçlar, RAG, skor, crew | `utils.py` |

**Ajanlar:** `Security_Auditor` → `Cyber_Security_Professor` → `Senior_Refactor_Engineer`

**Araçlar:** `run_static_security_scan`, `search_owasp_knowledge`

## Kurulum (senin yapman gerekenler)

1. **Python 3.10–3.13** önerilir (`python --version`). **3.13** kullanıyorsan bu repo **CrewAI 1.x** ister (`requirements.txt`); eski `crewai<1` bu sürümde kurulamaz.
2. **Sanal ortamı proje klasöründe oluştur:** `C:\Users\...\secure-code-mentor` içinde `python -m venv .venv` (venv’i `C:\Users\kagan` gibi üst klasörde oluşturma; `requirements.txt` orada yoktur).
3. Repoyu klonla veya bu klasörde kal:

   ```bash
   git clone https://github.com/kaganay/secure-code-mentor.git
   cd secure-code-mentor
   ```

4. Sanal ortam ve bağımlılıklar (komutları **proje kökünde** çalıştır):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

5. **Ortam değişkenleri:** `.env.example` dosyasını `.env` olarak kopyala ve düzenle:

   - `OPENAI_API_KEY` (veya `GROQ_API_KEY` + isteğe bağlı `GROQ_MODEL`)
   - CrewAI `memory` embedding hatası alırsan geçici olarak: `SECURECODE_DISABLE_MEMORY=1`

6. **OWASP PDF (isteğe bağlı):** `knowledge/` klasörüne PDF koy; uygulama ilk çalışmada Chroma indeksini `data/chroma/` altında oluşturur.

**Groq:** Kurulum hatası veya model hatası alırsan `pip install litellm` deneyebilir veya CrewAI dokümantasyonundaki Groq entegrasyonuna bak.

## Çalıştırma

```bash
streamlit run app.py
```

CLI:

```bash
python main.py --file examples/insecure_sample.py
```

## Demo kodu

`examples/insecure_sample.py` bilinçli olarak zayıf örnekler içerir; arayüzde yükleyip analiz edebilirsin.

## Lisans

Ders / kişisel proje kullanımı için; ihtiyaç halinde MIT veya benzeri lisans ekleyebilirsin.
