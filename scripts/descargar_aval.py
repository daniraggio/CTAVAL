"""
descargar_aval.py
Ruta en el repo: scripts/descargar_aval.py
"""

import shutil
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL   = "http://orazul.cilary.com/"
BUSQUEDA   = "aval"
MAQUINA    = "c.termica alto valle"
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
        if (window.$ && $(sel).selectpicker) $(sel).selectpicker('refresh');
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

        # 3. Escribir en buscador
        print(f"  → Buscando '{BUSQUEDA}'...")
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

        # 4. Seleccionar máquina
        print("  → Seleccionando máquina...")
        page.locator("li, a, span, div").filter(has_text=MAQUINA).first.click()
        page.wait_for_timeout(1_000)
        guardar_debug(page, "01_maquina")

        # 5. Click Generar y esperar el link — solo links de orazul.cilary.com
        print("  → Generando archivo...")
        page.get_by_role("button", name="Generar").click()

        # Esperar link que apunte al servidor orazul (no a github)
        link_xls = page.locator("a[href*='orazul'][href*='.xls'], a[href*='cilary'][href*='.xls']")
        
        # Si no tiene dominio completo, buscar por href relativo
        if link_xls.count() == 0:
            link_xls = page.locator("a[href$='.xls']:not([href*='github'])")

        link_xls.wait_for(timeout=30_000)
        
        # Loguear el href real antes de descargar
        href = link_xls.first.get_attribute("href")
        print(f"  → Link encontrado: {href}")
        guardar_debug(page, "02_link_listo")

        # 6. Descargar interceptando la respuesta de red
        with page.expect_download(timeout=30_000) as dl_info:
            link_xls.first.click()

        download = dl_info.value
        
        # Verificar que lo descargado es realmente un XLS (no HTML)
        tmp = download.path()
        with open(tmp, 'rb') as f:
            header = f.read(8)
        
        # XLS real empieza con D0 CF 11 E0 (formato OLE2) o PK (xlsx)
        if header[:4] in [b'\xd0\xcf\x11\xe0', b'PK\x03\x04']:
            shutil.copy(tmp, destino)
            print(f"  ✅ XLS válido guardado: {destino}")
        else:
            # Es HTML u otra cosa — intentar descarga directa via URL
            print(f"  ⚠ Archivo descargado no es XLS válido (header: {header[:4].hex()})")
            print(f"  → Intentando descarga directa desde: {href}")
            
            if href and not href.startswith('http'):
                href = BASE_URL.rstrip('/') + '/' + href.lstrip('/')
            
            import urllib.request
            urllib.request.urlretrieve(href, destino)
            
            with open(destino, 'rb') as f:
                header2 = f.read(8)
            print(f"  → Header descarga directa: {header2[:4].hex()}")
            
            if header2[:4] not in [b'\xd0\xcf\x11\xe0', b'PK\x03\x04']:
                raise ValueError(f"El archivo descargado no es un XLS válido. Header: {header2[:4].hex()}")
            
            print(f"  ✅ XLS válido guardado via URL directa: {destino}")

        browser.close()

    return destino


if __name__ == "__main__":
    try:
        archivo = descargar_planilla()
        print(f"\n✅ Listo: {archivo}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
