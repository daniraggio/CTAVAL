"""
descargar_aval.py
-----------------
Descarga la planilla XLS mensual de la Central Térmica Alto Valle
desde orazul.cilary.com y la guarda en /data/ del repo.

Ruta en el repo: scripts/descargar_aval.py
"""

import shutil
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_URL    = "http://orazul.cilary.com/"
BUSQUEDA    = "aval"
MAQUINA     = "AVAL - CTALVALG - c.termica alto valle"
OUTPUT_DIR  = Path(__file__).resolve().parent.parent / "data"
# ───────────────────────────────────────────────────────────────────────────────


def nombre_archivo():
    now = datetime.now()
    return f"AVAL_{now.year}_{now.month:02d}.xls"


def mes_en_español():
    meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    return meses[datetime.now().month]


def descargar_planilla():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destino = OUTPUT_DIR / nombre_archivo()
    now     = datetime.now()

    print(f"[{now:%H:%M:%S}] Iniciando → {destino.name}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page    = context.new_page()

        # 1. Abrir sitio y hacer click en "Posoperativo"
        print("  → Abriendo sitio...")
        page.goto(BASE_URL, timeout=30_000)
        page.wait_for_load_state("networkidle")
        page.get_by_text("Posoperativo", exact=True).click()
        page.wait_for_load_state("networkidle")

        # 2. Seleccionar Año en el primer dropdown
        print(f"  → Seleccionando año {now.year}...")
        page.locator("select").nth(0).select_option(str(now.year))
        page.wait_for_timeout(500)

        # 3. Seleccionar Mes en el segundo dropdown
        mes = mes_en_español()
        print(f"  → Seleccionando mes {mes}...")
        page.locator("select").nth(1).select_option(label=mes)
        page.wait_for_timeout(500)

        # 4. Escribir "aval" en el campo de búsqueda
        print(f"  → Buscando '{BUSQUEDA}'...")
        page.locator("input[type='text']").first.fill(BUSQUEDA)
        page.wait_for_timeout(800)

        # 5. Seleccionar "AVAL - CTALVALG - c.termica alto valle" de la lista
        print(f"  → Seleccionando máquina...")
        page.get_by_text(MAQUINA, exact=False).first.click()
        page.wait_for_timeout(500)

        # 6. Click en "Generar"
        print("  → Generando archivo...")
        page.get_by_role("button", name="Generar").click()
        page.wait_for_timeout(3_000)  # esperar que aparezca el link

        # 7. Descargar el archivo XLS generado
        print("  → Descargando...")
        with page.expect_download(timeout=30_000) as dl_info:
            page.locator(f"a[href*='.xls']").first.click()

        download  = dl_info.value
        tmp_path  = download.path()
        shutil.copy(tmp_path, destino)

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
