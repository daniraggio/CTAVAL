"""
descargar_aval.py
-----------------
Descarga las planillas XLS de la Central Térmica Alto Valle.

Lógica:
- Siempre descarga el mes actual
- Si estamos en los primeros N días del mes, también re-descarga el mes anterior
  porque puede tener días nuevos publicados con demora (fines de semana, etc.)

Ruta en el repo: scripts/descargar_aval.py
"""

import requests, json, calendar
from datetime import datetime, date, timedelta
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / 'data' / 'config.json'

BASE_URL   = "http://orazul.cilary.com"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"

GRUPOS = ["AVALTV12", "AVALTV11", "AVALTG22", "AVALTG21",
          "AVALTG23", "AVALCC22", "AVALCC23"]

# Cuántos días del mes nuevo esperamos antes de dejar de actualizar el anterior
DIAS_SOLAPE = 5


def meses_a_descargar():
    """Devuelve lista de (year, month) a descargar."""
    hoy = date.today()
    meses = [(hoy.year, hoy.month)]

    # Si estamos en los primeros DIAS_SOLAPE días, también actualizamos el mes anterior
    if hoy.day <= DIAS_SOLAPE:
        if hoy.month == 1:
            meses.append((hoy.year - 1, 12))
        else:
            meses.append((hoy.year, hoy.month - 1))

    return meses


def dias_en_mes(year, month):
    return calendar.monthrange(year, month)[1]


def descargar_mes(session, year, month):
    nombre_local = f"AVAL_{year}_{month:02d}.xls"
    destino = OUTPUT_DIR / nombre_local

    print(f"\n  📅 Descargando {year}/{month:02d}...")

    payload = [("grupos[]", g) for g in GRUPOS] + [
        ("contrato", "Ninguno"),
        ("anio",     str(year)),
        ("mes",      str(month)),
    ]

    import time
    for attempt in range(2):
        try:
            resp = session.post(f"{BASE_URL}/get_report", data=payload, timeout=60)
            resp.raise_for_status()
            break
        except requests.exceptions.HTTPError as e:
            if attempt == 0:
                print(f"     ⚠ Error en intento 1: {e} — reintentando en 60s...")
                time.sleep(60)
            else:
                raise
    nombre_servidor = resp.text.strip()
    print(f"     Servidor: {nombre_servidor!r}")

    if not nombre_servidor.endswith(".xls"):
        raise ValueError(f"Respuesta inesperada: {nombre_servidor!r}")

    url_xls = f"{BASE_URL}/static/reports/{nombre_servidor}"
    dl = session.get(url_xls, timeout=60)
    dl.raise_for_status()

    if dl.content[:4] != b'\xd0\xcf\x11\xe0':
        raise ValueError(f"Archivo no es XLS válido. Header: {dl.content[:4].hex()}")

    destino.write_bytes(dl.content)

    total_dias = dias_en_mes(year, month)
    hoy = date.today()
    # Días esperados: si es el mes actual, hasta ayer (con 1-2 días de demora)
    dias_esperados = total_dias if (year, month) != (hoy.year, hoy.month) else hoy.day - 2
    kb = len(dl.content) // 1024

    print(f"     ✅ {nombre_local} ({kb} KB) — mes tiene {total_dias} días")
    return destino


def fetch_tc_bcra(year, month):
    """Obtiene TC mayorista (≈ Com.A 3500) desde dolarapi.com/v1/dolares/mayorista.
    Fuente actualizada a diario, sin lag, CORS abierto."""
    try:
        resp = requests.get("https://dolarapi.com/v1/dolares/mayorista", timeout=20)
        resp.raise_for_status()
        data = resp.json()
        tc = float(data.get("venta", 0))
        fecha_iso = data.get("fechaActualizacion", "")
        fecha_v = fecha_iso[:10] if fecha_iso else str(date.today())
        if tc > 0:
            print(f"     TC mayorista {year}/{month:02d}: ${tc:,.4f} ({fecha_v})")
            return tc, fecha_v
        print("     ⚠ Valor inválido")
    except Exception as e:
        print(f"     ⚠ Error: {type(e).__name__}: {e}")
    return None, None


def update_config_tc(meses):
    """Actualiza TC en config.json para cada mes."""
    cfg = {}
    if CONFIG_PATH.exists():
        try: cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        except: pass
    month_cfg = cfg.setdefault("MONTH_CFG", {})
    updated = False
    for year, month in meses:
        tc, tc_date = fetch_tc_bcra(year, month)
        if tc:
            mk = f"{year}_{month:02d}"
            month_cfg.setdefault(mk, {}).update({"TC": tc, "TCDate": tc_date})
            updated = True
    if updated:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')
        print("     ✅ config.json actualizado con TC Com.3500")


def descargar_planillas():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    print(f"[{now:%H:%M:%S}] Iniciando descarga...")

    meses = meses_a_descargar()
    print(f"  Meses a descargar: {meses}")

    session = requests.Session()
    session.headers.update({
        "Referer": BASE_URL + "/",
        "Origin":  BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
    })

    for year, month in meses:
        descargar_mes(session, year, month)

    print(f"\n✅ Descarga completada ({len(meses)} archivo/s)")
    update_config_tc(meses)


if __name__ == "__main__":
    try:
        descargar_planillas()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
