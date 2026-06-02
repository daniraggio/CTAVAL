"""
send_resumen.py
---------------
Genera el resumen del mes actual a partir del XLS descargado
y lo manda por mail via Resend API.

Ruta en el repo: scripts/send_resumen.py
"""

import json
import os
import requests
from datetime import datetime
from pathlib import Path

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "re_ZwDtQ1e7_7WXxMVzRhuGffmoi7LSNwxz8")
FROM_EMAIL     = "onboarding@resend.dev"
TO_EMAILS      = ["danielraggio@gmail.com"]  # prueba — cambiar cuando el dominio esté verificado
DASHBOARD_URL  = "https://daniraggio.github.io/CTAVAL/"
DATA_DIR       = Path(__file__).resolve().parent.parent / "data"

MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]


def nombre_archivo():
    now = datetime.now()
    return f"AVAL_{now.year}_{now.month:02d}.xls"


def get_file_info():
    f = DATA_DIR / nombre_archivo()
    if not f.exists():
        return None
    return {"name": f.name, "size_kb": f.stat().st_size // 1024}


def parse_xls_resumen():
    """Lee el XLS y extrae valores clave del resumen."""
    try:
        import xlrd
        f = DATA_DIR / nombre_archivo()
        if not f.exists():
            return None
        wb = xlrd.open_workbook(str(f))
        # Intentar leer datos básicos de energía de la primera hoja disponible
        sheets = wb.sheet_names()
        energia_total = 0
        for sh_name in sheets:
            if 'ENERGIA' in sh_name:
                sh = wb.sheet_by_name(sh_name)
                for row_i in range(2, sh.nrows):
                    try:
                        vals = [sh.cell_value(row_i, c) for c in range(2, 26)]
                        energia_total += sum(v for v in vals if isinstance(v, (int, float)) and v > 0)
                    except:
                        pass
        return {"energia_total": round(energia_total)}
    except Exception as e:
        print(f"  ⚠ No se pudo leer XLS: {e}")
        return None


def fmt_num(n):
    return f"{n:,.0f}".replace(",", ".")


def build_html_email(file_info, resumen):
    now = datetime.now()
    mes = MESES[now.month-1]
    fecha_str = now.strftime("%d/%m/%Y %H:%M")

    file_row = ""
    if file_info:
        file_row = f"""<tr>
          <td style="padding:8px 0;border-bottom:1px solid #21262d;color:#8b949e;font-size:13px">Archivo</td>
          <td style="padding:8px 0;border-bottom:1px solid #21262d;font-size:13px;color:#e6edf3">{file_info['name']} ({file_info['size_kb']} KB)</td>
        </tr>"""

    resumen_rows = ""
    if resumen and resumen.get("energia_total"):
        resumen_rows = f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px">
          <div style="font-size:13px;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.06em;margin-bottom:12px">Producción</div>
          <table style="width:100%;border-collapse:collapse">
            <tr>
              <td style="padding:8px 0;color:#8b949e;font-size:13px">Energía generada</td>
              <td style="padding:8px 0;font-size:18px;font-weight:700;color:#e6edf3;font-family:monospace">{fmt_num(resumen['energia_total'])} MWh</td>
            </tr>
          </table>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0d1117;font-family:system-ui,sans-serif">
  <div style="max-width:600px;margin:0 auto;padding:32px 16px">

    <div style="margin-bottom:24px">
      <div style="font-size:22px;font-weight:700;color:#e6edf3">Central Térmica Alto Valle</div>
      <div style="font-size:14px;color:#8b949e;margin-top:4px">Actualización diaria — {fecha_str}</div>
    </div>

    <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px">
      <div style="font-size:13px;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.06em;margin-bottom:12px">Período</div>
      <table style="width:100%;border-collapse:collapse">
        <tr>
          <td style="padding:8px 0;border-bottom:1px solid #21262d;color:#8b949e;font-size:13px">Mes en análisis</td>
          <td style="padding:8px 0;border-bottom:1px solid #21262d;font-size:13px;font-weight:600;color:#e6edf3">{mes} {now.year}</td>
        </tr>
        {file_row}
      </table>
    </div>

    {resumen_rows}

    <div style="text-align:center;margin:28px 0">
      <a href="{DASHBOARD_URL}"
         style="background:#238636;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:6px;font-weight:600;font-size:14px;display:inline-block">
        Ver Dashboard Completo →
      </a>
    </div>

    <div style="font-size:11px;color:#484f58;text-align:center;margin-top:24px">
      Este mail se genera automáticamente todos los días a las 8 AM.
    </div>
  </div>
</body>
</html>"""


def send_email(html_body, subject):
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "from": FROM_EMAIL,
            "to": TO_EMAILS,
            "subject": subject,
            "html": html_body
        },
        timeout=30
    )
    if not resp.ok:
        raise Exception(f"Error {resp.status_code}: {resp.text}")
    data = resp.json()
    print(f"  ✅ Mail enviado — ID: {data.get('id')}")
    return data


if __name__ == "__main__":
    now = datetime.now()
    mes = MESES[now.month-1]

    print(f"[{now:%H:%M:%S}] Generando resumen...")
    file_info = get_file_info()
    resumen = parse_xls_resumen()
    html = build_html_email(file_info, resumen)
    subject = f"Central Térmica Alto Valle — {mes} {now.year} actualizado"

    print(f"  → Enviando a: {', '.join(TO_EMAILS)}")
    try:
        send_email(html, subject)
    except Exception as e:
        print(f"  ❌ Error: {e}")
        raise


def nombre_archivo():
    now = datetime.now()
    return f"AVAL_{now.year}_{now.month:02d}.xls"


def get_file_info():
    """Info básica del archivo descargado."""
    f = DATA_DIR / nombre_archivo()
    if not f.exists():
        return None
    size_kb = f.stat().st_size // 1024
    return {"name": f.name, "size_kb": size_kb}


def build_html_email(file_info):
    now = datetime.now()
    mes = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
           "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][now.month-1]
    fecha_str = now.strftime("%d/%m/%Y %H:%M")

    file_section = ""
    if file_info:
        file_section = f"""
        <tr>
          <td style="padding:8px 0;color:#8b949e;font-size:13px">Archivo actualizado</td>
          <td style="padding:8px 0;font-size:13px;font-weight:600">{file_info['name']} ({file_info['size_kb']} KB)</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0d1117;font-family:system-ui,sans-serif">
  <div style="max-width:600px;margin:0 auto;padding:32px 16px">

    <div style="margin-bottom:24px">
      <div style="font-size:22px;font-weight:700;color:#e6edf3">C. Térmica Alto Valle</div>
      <div style="font-size:14px;color:#8b949e;margin-top:4px">Actualización diaria — {fecha_str}</div>
    </div>

    <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px">
      <div style="font-size:13px;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.06em;margin-bottom:12px">Período</div>
      <table style="width:100%;border-collapse:collapse">
        <tr>
          <td style="padding:8px 0;color:#8b949e;font-size:13px">Mes en análisis</td>
          <td style="padding:8px 0;font-size:13px;font-weight:600;color:#e6edf3">{mes} {now.year}</td>
        </tr>
        {file_section}
      </table>
    </div>

    <div style="text-align:center;margin:28px 0">
      <a href="{DASHBOARD_URL}"
         style="background:#238636;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:6px;font-weight:600;font-size:14px;display:inline-block">
        Ver Dashboard Completo →
      </a>
    </div>

    <div style="font-size:11px;color:#484f58;text-align:center;margin-top:24px">
      Este mail se genera automáticamente todos los días a las 8 AM.
    </div>
  </div>
</body>
</html>"""


def send_email(html_body, subject):
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "from": FROM_EMAIL,
            "to": TO_EMAILS,
            "subject": subject,
            "html": html_body
        },
        timeout=30
    )
    if not resp.ok:
        raise Exception(f"Error {resp.status_code}: {resp.text}")
    data = resp.json()
    print(f"  ✅ Mail enviado — ID: {data.get('id')}")
    return data


if __name__ == "__main__":
    now = datetime.now()
    mes = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
           "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][now.month-1]

    print(f"[{now:%H:%M:%S}] Generando resumen...")
    file_info = get_file_info()
    html = build_html_email(file_info)
    subject = f"C. Térmica Alto Valle — {mes} {now.year} actualizado"

    print(f"  → Enviando a: {', '.join(TO_EMAILS)}")
    try:
        send_email(html, subject)
    except Exception as e:
        print(f"  ❌ Error: {e}")
        raise
