"""
descargar_aval.py
-----------------
Descarga la planilla XLS mensual de la Central Térmica Alto Valle
desde orazul.cilary.com. Los dropdowns usan Bootstrap Selectpicker
(el <select> nativo está oculto), por eso se interactúa via JS + click.

Ruta en el repo: scripts/descargar_aval.py
"""

import shutil
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL   = "http://orazul.cilary.com/"
BUSQUEDA   = "aval"
MAQUINA    = "AVAL - CTALVALG - c.termica alto valle"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"

MESES_ES = {
    1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril",
    5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto",
    9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"
}


def nombre_archivo():
    now = datetime.now()
    return f"AVAL_{now.year}_{now.month:02d}.xls"


def selectpicker_elegir(page, select_id, valor):
    """
    Selecciona una opción en un Bootstrap Selectpicker.
    Estrategia: forzar el valor via JS y luego disparar 'change'.
    """
    page.evaluate(f"""
        var sel = document.getElementById('{select_id}');
        sel.value = '{valor}';
        sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
        if (typeof $(sel).selectpicker !== 'undefined') {{
            $(sel).selectpicker('refresh');
        }}
    """)
    page.wait_for_timeout(800)


def descargar_planilla():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destino = OUTPUT_DIR / nombre_archivo()
    now     = datetime.now()

    print(f"[{now:%H:%M:%S}] Iniciando → {destino.name}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page    = context.new_page()

        # 1. Abrir sitio
        print("  → Abriendo sitio...")
        page.goto(BASE_URL, timeout=30_000)
        page.wait_for_load_state("networkidle")

        # 2. Click en tab "Posoperativo"
        print("  → Navegando a Posoperativo...")
        page.get_by_text("Posoperativo", exact=True).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1_000)

        # 3. Seleccionar Año via JS (Bootstrap Selectpicker)
        print(f"  → Seleccionando año {now.year}...")
        selectpicker_elegir(page, "anio", str(now.year))

        # 4. Seleccionar Mes via JS
        mes_num = str(now.month)
        print(f"  → Seleccionando mes {MESES_ES[now.month]} ({mes_num})...")
        selectpicker_elegir(page, "mes", mes_num)

        # 5. Escribir "aval" en el buscador de máquinas
        print(f"  → Buscando máquina '{BUSQUEDA}'...")
        page.locator("input[type='text']").first.fill(BUSQUEDA)
        page.wait_for_timeout(1_000)

        # 6. Seleccionar "AVAL - CTALVALG - c.termica alto valle"
        print("  → Seleccionando AVAL - CTALVALG - c.termica alto valle...")
        page.get_by_text(MAQUINA, exact=False).first.click()
        page.wait_for_timeout(500)

        # 7. Click en "Generar"
        print("  → Generando archivo...")
        page.get_by_role("button", name="Generar").click()
        page.wait_for_timeout(4_000)

        # 8. Descargar el .xls que aparece como link
        print("  → Descargando .xls...")
        with page.expect_download(timeout=30_000) as dl_info:
            page.locator("a[href*='.xls']").first.click()

        download = dl_info.value
        shutil.copy(download.path(), destino)

        print(f"  ✅ Guardado: {destino}")
        browser.close()

    return destino


if __name__ == "__main__":
    try:
        archivo = descargar_planilla()
        print(f"\n✅ Listo: {archivo}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
