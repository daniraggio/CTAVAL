"""
send_resumen.py
Toma screenshot del dashboard, lo sube a GitHub y manda el mail con URL pública.
Ruta en el repo: scripts/send_resumen.py
"""

import os, base64, requests, json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

RESEND_API_KEY  = os.environ.get("RESEND_API_KEY", "re_ZwDtQ1e7_7WXxMVzRhuGffmoi7LSNwxz8")
GH_TOKEN        = os.environ.get("GITHUB_TOKEN", "")
REPO            = "daniraggio/CTAVAL"
FROM_EMAIL      = "onboarding@resend.dev"
TO_EMAILS       = ["danielraggio@gmail.com", "draggio@aconcaguaenergia.com", "jspinoso@aconcaguaenergia.com"]
DASHBOARD_URL   = "https://daniraggio.github.io/CTAVAL/"
SCREENSHOT_PATH = Path("/tmp/resumen.png")
IMG_REPO_PATH   = "screenshots/resumen_latest.png"
IMG_PUBLIC_URL  = f"https://raw.githubusercontent.com/{REPO}/main/{IMG_REPO_PATH}"

MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]


def take_screenshot():
    print("  → Abriendo dashboard...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(DASHBOARD_URL, timeout=60_000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(6_000)
        try:
            page.locator("#sec-resumen").screenshot(path=str(SCREENSHOT_PATH))
        except:
            page.screenshot(path=str(SCREENSHOT_PATH))
        browser.close()
    print(f"  → Screenshot: {SCREENSHOT_PATH.stat().st_size // 1024} KB")


def upload_screenshot_to_github():
    print("  → Subiendo screenshot a GitHub...")
    hdrs = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    content = base64.b64encode(SCREENSHOT_PATH.read_bytes()).decode()

    # Get current SHA if exists
    sha = None
    meta = requests.get(f"https://api.github.com/repos/{REPO}/contents/{IMG_REPO_PATH}", headers=hdrs)
    if meta.ok:
        sha = meta.json().get("sha")

    body = {"message": "screenshot update", "content": content, "branch": "main"}
    if sha:
        body["sha"] = sha

    resp = requests.put(
        f"https://api.github.com/repos/{REPO}/contents/{IMG_REPO_PATH}",
        headers=hdrs, json=body, timeout=60
    )
    if not resp.ok:
        raise Exception(f"GitHub upload error: {resp.text}")
    print(f"  → Imagen disponible en: {IMG_PUBLIC_URL}")


def build_html_email():
    now = datetime.now()
    mes = MESES[now.month-1]
    fecha_str = now.strftime("%d/%m/%Y %H:%M")
    # Agregar timestamp para evitar cache del mail
    img_url = f"{IMG_PUBLIC_URL}?t={int(now.timestamp())}"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0d1117;font-family:system-ui,sans-serif">
  <div style="max-width:700px;margin:0 auto;padding:32px 16px">
    <div style="margin-bottom:24px">
      <div style="font-size:22px;font-weight:700;color:#e6edf3">Central Térmica Alto Valle</div>
      <div style="font-size:14px;color:#8b949e;margin-top:4px">Actualización diaria — {fecha_str}</div>
    </div>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px">
      <div style="font-size:13px;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.06em;margin-bottom:12px">Resumen — {mes} {now.year}</div>
      <img src="{img_url}" width="640" style="width:100%;border-radius:6px;display:block" alt="Resumen del mes"/>
    </div>
    <div style="text-align:center;margin:28px 0">
      <a href="{DASHBOARD_URL}" style="background:#238636;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:6px;font-weight:600;font-size:14px;display:inline-block">
        Ver Dashboard Completo →
      </a>
    </div>
    <div style="font-size:11px;color:#484f58;text-align:center;margin-top:24px">
      Este mail se genera automáticamente todos los días a las 8 AM.
    </div>
  </div>
</body>
</html>""", f"Central Térmica Alto Valle — {mes} {now.year} actualizado"


def send_email(html_body, subject):
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        json={"from": FROM_EMAIL, "to": TO_EMAILS, "subject": subject, "html": html_body},
        timeout=30
    )
    if not resp.ok:
        raise Exception(f"Error {resp.status_code}: {resp.text}")
    print(f"  ✅ Mail enviado — ID: {resp.json().get('id')}")


if __name__ == "__main__":
    now = datetime.now()
    print(f"[{now:%H:%M:%S}] Generando resumen...")
    try:
        take_screenshot()
        upload_screenshot_to_github()
        html, subject = build_html_email()
        print(f"  → Enviando a: {', '.join(TO_EMAILS)}")
        send_email(html, subject)
    except Exception as e:
        print(f"  ❌ Error: {e}")
        raise
