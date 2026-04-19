# SecureCode Mentor

Freelance ve öğrenci geliştiriciler için **OWASP odaklı** çoklu ajan (CrewAI) kod güvenliği mentoru: statik sinyaller, RAG ile literatür desteği, eğitimsel açıklama ve güvenli refaktör önerisi.

**GitHub:** [kaganay/secure-code-mentor](https://github.com/kaganay/secure-code-mentor)

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
