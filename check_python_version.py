"""
Kurulum öncesi: CrewAI 1.x bu projede yalnızca Python 3.10–3.13 ile desteklenir.

Çalıştır: python check_python_version.py
Uygunsa çıkış kodu 0, değilse 1 ve açıklama yazdırır.
"""

from __future__ import annotations

import sys


def main() -> int:
    v = sys.version_info
    ok = (3, 10) <= (v.major, v.minor) <= (3, 13)
    ver = f"{v.major}.{v.minor}.{v.micro}"
    if ok:
        print(f"Python {ver} — CrewAI / bu repo ile uyumlu aralık (3.10–3.13).")
        return 0
    if (v.major, v.minor) < (3, 10):
        print(f"Python {ver} — ÇOK ESKİ. 3.10 veya üzeri kur (tercihen 3.12).")
    else:
        print(
            f"Python {ver} — CrewAI 1.x şu an PyPI'da genelde <3.14 ister; "
            f"bu yüzden pip eski crewai listesine düşüyor.\n"
            f"Çözüm: python.org'dan Python 3.12 veya 3.13 kur; venv'i o python ile oluştur:\n"
            f'  py -3.12 -m venv .venv\n'
            f"  veya kurulum yolundaki python.exe ile -m venv .venv",
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
