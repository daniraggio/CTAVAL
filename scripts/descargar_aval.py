"""
descargar_aval.py
Ruta en el repo: scripts/descargar_aval.py
"""

import requests
from datetime import datetime
from pathlib import Path

BASE_URL   = "http://orazul.cilary.com"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"

GRUPOS = ["AVALTV12", "AVALTV11", "AVALTG22", "AVALTG21",
          "AVALTG23", "AVALCC22", "AVALCC23"]


def descargar_planilla():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    destino = OUTPUT_DIR / f"AVAL_{now.year}_{now.month:02d}.xls"

    print(f"[{now:%H:%M:%S}] Iniciando descarga {now.year}/{now.month}...")

    session = requests.Session()
    session.headers.update({
        "Referer": BASE_URL + "/",
        "Origin":  BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
    })

    # Payload exacto que manda el browser
    payload = [("grupos[]", g) for g in GRUPOS] + [
        ("contrato", "Ninguno"),
        ("anio",     str(now.year)),
        ("mes",      str(now.month)),
    ]

    print("  → Solicitando reporte...")
    resp = session.post(f"{BASE_URL}/get_report", data=payload, timeout=60)
    resp.raise_for_status()
    nombre_servidor = resp.text.strip()
    print(f"  → Servidor devolvió: {nombre_servidor!r}")

    if not nombre_servidor.endswith(".xls"):
        raise ValueError(f"Respuesta inesperada: {nombre_servidor!r}")

    url_xls = f"{BASE_URL}/static/reports/{nombre_servidor}"
    print(f"  → Descargando: {url_xls}")

    dl = session.get(url_xls, timeout=60)
    dl.raise_for_status()

    if dl.content[:4] != b'\xd0\xcf\x11\xe0':
        raise ValueError(f"Archivo no es XLS válido. Header: {dl.content[:4].hex()}")

    destino.write_bytes(dl.content)
    print(f"  ✅ Guardado: {destino.name} ({len(dl.content):,} bytes)")
    return destino


if __name__ == "__main__":
    try:
        archivo = descargar_planilla()
        print(f"\n✅ Listo: {archivo}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
