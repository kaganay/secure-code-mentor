"""
Kurulum öncesi: CrewAI 1.x bu projede yalnızca Python 3.10–3.13 ile desteklenir.

Önerilen çalıştırma (PATH karışmasını önler):
  .\\.venv\\Scripts\\python.exe check_python_version.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def _looks_like_project_venv() -> bool:
    """Windows'ta 'Activate' sonrası bile global python seçilebiliyor; yolu kontrol eder."""
    exe = str(Path(sys.executable).resolve()).lower().replace("/", "\\")
    return ".venv\\scripts\\python" in exe or ".venv/scripts/python" in exe


def main() -> int:
    exe = Path(sys.executable).resolve()
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    in_venv = _looks_like_project_venv()

    if not in_venv and (v.major, v.minor) >= (3, 10):
        print(
            "UYARI: Çalışan Python sanal ortamdaki gibi görünmüyor.\n"
            f"  sys.executable = {exe}\n"
            "Windows bazen PATH'te 3.14'ü öne alır; komutları şöyle çalıştır:\n"
            r"  .\.venv\Scripts\python.exe check_python_version.py"
            "\n"
            r"  .\.venv\Scripts\python.exe -m pip install -r requirements.txt",
        )
        print()

    ok = (3, 10) <= (v.major, v.minor) <= (3, 13)
    if ok:
        print(f"Python {ver} — CrewAI / bu repo ile uyumlu aralık (3.10–3.13).")
        if in_venv:
            print("Sanal ortam yolu doğru görünüyor (.venv\\Scripts\\python).")
        return 0

    if (v.major, v.minor) < (3, 10):
        print(f"Python {ver} — ÇOK ESKİ. 3.10 veya üzeri kur (tercihen 3.12).")
    else:
        print(
            f"Python {ver} — CrewAI 1.x PyPI sürümleri şu an genelde Requires-Python: <3.14.\n"
            "Çözüm A — 3.12/3.13 ile venv (önerilen):\n"
            "  py -3.12 -m venv .venv\n"
            r"  .\.venv\Scripts\python.exe -m pip install -U pip"
            "\n"
            r"  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
            "\n\n"
            "Çözüm B — PATH karışıyorsa her zaman tam yol kullan (yukarıdaki .venv\\Scripts\\python.exe).",
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
