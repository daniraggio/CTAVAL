"""
descargar_aval.py - con debug mode para inspeccionar el DOM
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
    """Guarda screenshot + HTML para inspección."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(DEBUG_DIR / f"{nombre}.png"), full_page=True)
    (DEBUG_DIR / f"{nombre}.html").write_text(page.content(), encoding="utf-8")
    print(f"  📸 Debug guardado: debug/{nombre}.png + .html")


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

        # 1. Abrir sitio
        print("  → Abriendo sitio...")
        page.goto(BASE_URL, timeout=30_000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2_000)
        guardar_debug(page, "01_inicio")

        # 2. Click en tab "Posoperativo"
        print("  → Navegando a Posoperativo...")
        page.get_by_text("Posoperativo", exact=True).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2_000)
        guardar_debug(page, "02_posoperativo")

        # 3. Mostrar todos los inputs/selects visibles
        elementos = page.evaluate("""
            () => {
                let info = [];
                document.querySelectorAll('input, select, button').forEach(el => {
                    info.push({
                        tag: el.tagName,
                        id: el.id,
                        name: el.name,
                        type: el.type,
                        class: el.className,
                        visible: el.offsetParent !== null,
                        placeholder: el.placeholder || ''
                    });
                });
                return info;
            }
        """)
        print("\n  📋 Elementos encontrados en el DOM:")
        for el in elementos:
            print(f"     {el['tag']} id={el['id']} name={el['name']} type={el['type']} visible={el['visible']} class={el['class'][:50]}")

        # 4. Año via JS
        print(f"\n  → Seleccionando año {now.year}...")
        selectpicker_elegir(page, "anio", str(now.year))
        guardar_debug(page, "03_anio")

        # 5. Mes via JS
        print(f"  → Seleccionando mes {MESES_ES[now.month]}...")
        selectpicker_elegir(page, "mes", str(now.month))
        guardar_debug(page, "04_mes")

        # 6. Buscar el input de búsqueda por id/name/placeholder en lugar de type
        print(f"  → Buscando campo de texto para '{BUSQUEDA}'...")
        # Intentar por JS directamente en el input de búsqueda
        page.evaluate(f"""
            () => {{
                let inputs = document.querySelectorAll('input');
                for (let inp of inputs) {{
                    if (inp.offsetParent !== null) {{  // solo visibles
                        inp.value = '{BUSQUEDA}';
                        inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        inp.dispatchEvent(new Event('keyup', {{ bubbles: true }}));
                        break;
                    }}
                }}
            }}
        """)
        page.wait_for_timeout(1_500)
        guardar_debug(page, "05_busqueda")

        # 7. Seleccionar la máquina de la lista
        print("  → Seleccionando AVAL - CTALVALG - c.termica alto valle...")
        page.get_by_text(MAQUINA, exact=False).first.click()
        page.wait_for_timeout(500)
        guardar_debug(page, "06_maquina")

        # 8. Click en "Generar"
        print("  → Generando archivo...")
        page.get_by_role("button", name="Generar").click()
        page.wait_for_timeout(4_000)
        guardar_debug(page, "07_generar")

        # 9. Descargar
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
