"""
descargar_aval.py
-----------------
Descarga la planilla XLS mensual de la Central Térmica Alto Valle
llamando directamente a la API POST /get_report de orazul.cilary.com.
No necesita navegador — usa solo requests.

Ruta en el repo: scripts/descargar_aval.py
"""

import requests
import shutil
from datetime import datetime
from pathlib import Path

BASE_URL   = "http://orazul.cilary.com"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"

# Grupos de AVAL - CTALVALG - c.termica alto valle
GRUPOS = ["AVALTV12", "AVALTV11", "AVALTG22", "AVALTG21",
          "AVALTG23", "AVALCC22", "AVALCC23"]


def nombre_archivo():
    now = datetime.now()
    return f"AVAL_{now.year}_{now.month:02d}.xls"


def descargar_planilla():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destino = OUTPUT_DIR / nombre_archivo()
    now     = datetime.now()

    print(f"[{now:%H:%M:%S}] Iniciando → {destino.name}")

    session = requests.Session()
    session.headers.update({"Referer": BASE_URL + "/", "Origin": BASE_URL})

    # 1. POST a /get_report para generar el archivo
    print(f"  → Solicitando reporte ({now.year}/{now.month})...")
    resp = session.post(
        f"{BASE_URL}/get_report",
        data={
            "grupos":   GRUPOS,
            "contrato": "",
            "anio":     str(now.year),
            "mes":      str(now.month),
        },
        timeout=60,
    )
    resp.raise_for_status()

    nombre_xls = resp.text.strip()
    print(f"  → Servidor generó: {nombre_xls}")

    if not nombre_xls.endswith(".xls"):
        raise ValueError(f"Respuesta inesperada del servidor: {nombre_xls!r}")

    # 2. Descargar el archivo desde /static/reports/
    url_xls = f"{BASE_URL}/static/reports/{nombre_xls}"
    print(f"  → Descargando desde: {url_xls}")

    dl = session.get(url_xls, timeout=60)
    dl.raise_for_status()

    # Validar que es un XLS real (OLE2 header = D0 CF 11 E0)
    if dl.content[:4] != b'\xd0\xcf\x11\xe0':
        raise ValueError(f"El archivo descargado no es un XLS válido. Header: {dl.content[:4].hex()}")

    destino.write_bytes(dl.content)
    print(f"  ✅ Guardado: {destino} ({len(dl.content):,} bytes)")

    return destino


if __name__ == "__main__":
    try:
        archivo = descargar_planilla()
        print(f"\n✅ Listo: {archivo}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
