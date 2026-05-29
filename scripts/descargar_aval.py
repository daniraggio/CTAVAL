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
    nombre_local = f"AVAL_{now.year}_{now.month:02d}.xls"
    destino = OUTPUT_DIR / nombre_local

    print(f"[{now:%H:%M:%S}] Iniciando descarga {now.year}/{now.month}...")

    session = requests.Session()
    session.headers.update({
        "Referer": BASE_URL + "/",
        "Origin":  BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
    })

    # jQuery $.ajax serializa arrays como "grupos[]=VAL1&grupos[]=VAL2"
    # requests con lista en data lo manda igual cuando la key termina en []
    # Probamos las dos formas y usamos la que devuelva un .xls válido
    payload_opciones = [
        # Opción A: key normal con lista (requests la repite automáticamente)
        [("grupos", g) for g in GRUPOS] +
        [("contrato", ""), ("anio", str(now.year)), ("mes", str(now.month))],

        # Opción B: key con corchetes (jQuery style)
        [("grupos[]", g) for g in GRUPOS] +
        [("contrato", ""), ("anio", str(now.year)), ("mes", str(now.month))],
    ]

    nombre_servidor = None
    for i, payload in enumerate(payload_opciones):
        print(f"  → Intentando payload opción {i+1}...")
        resp = session.post(f"{BASE_URL}/get_report", data=payload, timeout=60)
        resp.raise_for_status()
        texto = resp.text.strip()
        print(f"     Respuesta: {texto!r}")
        if texto.endswith(".xls"):
            nombre_servidor = texto
            break

    if not nombre_servidor:
        raise ValueError(f"Ningún payload generó un .xls válido")

    url_xls = f"{BASE_URL}/static/reports/{nombre_servidor}"
    print(f"  → Descargando: {url_xls}")

    dl = session.get(url_xls, timeout=60)
    dl.raise_for_status()

    if dl.content[:4] != b'\xd0\xcf\x11\xe0':
        raise ValueError(f"Archivo no es XLS válido. Header: {dl.content[:4].hex()}\nContenido: {dl.content[:200]}")

    destino.write_bytes(dl.content)
    print(f"  ✅ Guardado: {nombre_local} ({len(dl.content):,} bytes)")
    return destino


if __name__ == "__main__":
    try:
        archivo = descargar_planilla()
        print(f"\n✅ Listo: {archivo}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
