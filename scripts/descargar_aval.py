"""
descargar_aval.py
Ruta en el repo: scripts/descargar_aval.py
"""

import shutil
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE_URL   = "http://orazul.cilary.com/"
BUSQUEDA   = "aval"
MAQUINA    = "AVAL - CTALVALG - c.termica alto valle"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
DEBUG_DIR  = Path(__file__).resolve().parent.parent / "debug"

MESES_ES = {
    1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril",
    5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto",
    9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"
}


def nombre_archivo():
    now = datetime.now()
    return f"AVAL_{now.year}_{now.month:02d}.xls"


def guardar_debug(page, nombre):
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(DEBUG_DIR / f"{nombre}.png"), full_page=True)
    print(f"  📸 {nombre}.png")


def selectpicker_elegir(page, select_id, valor):
    page.evaluate(f"""
        var sel = document.getElementById('{select_id}');
        sel.value = '{valor}';
        sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
        if (window.$ && $(sel).selectpicker) {{
            $(sel).selectpicker('refresh');
        }}
    """)
    page.wait_for_timeout(1_000)


def descargar_planilla():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destino = OUTPUT_DIR / nombre_archivo()
    now     = datetime.now()

    print(f"[{now:%H:%M:%S}] Iniciando → {destino.name}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page    = context.new_page()

        # 1. Abrir sitio y click en Posoperativo
        print("  → Abriendo sitio...")
        page.goto(BASE_URL, timeout=30_000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1_500)
        page.get_by_text("Posoperativo", exact=True).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1_500)

        # 2. Año y Mes via JS
        print(f"  → Año {now.year} / Mes {MESES_ES[now.month]}...")
        selectpicker_elegir(page, "anio", str(now.year))
        selectpicker_elegir(page, "mes", str(now.month))
        guardar_debug(page, "01_dropdowns")

        # 3. Escribir "aval" en el input visible
        print(f"  → Escribiendo '{BUSQUEDA}' en buscador...")
        # El input de búsqueda es el único visible en ese momento
        page.evaluate(f"""
            () => {{
                let inputs = Array.from(document.querySelectorAll('input[type=text]'));
                let visible = inputs.find(i => i.offsetParent !== null);
                if (visible) {{
                    visible.focus();
                    visible.value = '{BUSQUEDA}';
                    visible.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    visible.dispatchEvent(new Event('keyup', {{ bubbles: true }}));
                }}
            }}
        """)
        page.wait_for_timeout(1_500)
        guardar_debug(page, "02_busqueda")

        # 4. Seleccionar la máquina — click directo sobre el elemento de la lista
        print("  → Seleccionando máquina...")
        # Buscar el primer elemento de la lista que contenga el texto
        maquina_loc = page.locator("li, a, span, div").filter(has_text="c.termica alto valle").first
        maquina_loc.click()
        page.wait_for_timeout(1_000)
        guardar_debug(page, "03_maquina_seleccionada")

        # 5. Click en Generar y esperar el link dinámicamente
        print("  → Generando archivo (esperando link)...")
        page.get_by_role("button", name="Generar").click()

        # Esperar hasta 30s a que aparezca el link .xls
        link_xls = page.locator("a[href*='.xls']")
        link_xls.wait_for(timeout=30_000)
        guardar_debug(page, "04_link_generado")

        # 6. Descargar
        print("  → Descargando...")
        with page.expect_download(timeout=30_000) as dl_info:
            link_xls.first.click()

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
