import time
import datetime as dt
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from jinja2 import Template

# =========================
# OUTPUT (ROOT del repo)
# =========================
OUT_DIR = Path("sentenze")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Base URL per GitHub Pages
SITE_BASE = "https://slartax.github.io/sentenze-bot"
LATEST_HTML_URL = f"{SITE_BASE}/sentenze/latest.html"
LATEST_PDF_URL  = f"{SITE_BASE}/sentenze/latest.pdf"

# =========================
# HTML TEMPLATE
# =========================
HTML_TPL = Template("""
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Riassunto sentenza - {{ date }}</title>
</head>
<body>
  <style>
    body {font-family: system-ui; max-width: 900px; margin: 40px auto; padding: 0 16px; line-height: 1.6;}
    pre {white-space: pre-wrap; background: #f6f6f6; padding: 16px; border-radius: 12px; border: 1px solid #ddd;}
  </style>

  <h1>Riassunto sentenza</h1>
  <div class="meta">
    <strong>Data:</strong> {{ date }} • <strong>Fonte:</strong> {{ source }}
  </div>

  <p>
    <a href="{{ latest_pdf_url }}" target="_blank" rel="noopener">⬇️ PDF originale</a>
    <a href="{{ latest_html_url }}" target="_blank" rel="noopener">🔗 Apri HTML</a>
  </p>

  {% if warning %}
    <p style="color:#b00020;"><strong>Nota:</strong> {{ warning }}</p>
  {% endif %}

  <pre>{{ text }}</pre>
</body>
</html>
""")

# =========================
# SELENIUM SETUP (HEADLESS)
# =========================
def make_driver():
    options = Options()
    options.add_argument("--headless")  # Chrome headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

# =========================
# MAIN SCRAPER
# =========================
def main():
    driver = make_driver()
    wait = WebDriverWait(driver, 30)

    print("Apro banca dati giurisprudenza…")
    driver.get("https://bancadatigiurisprudenza.giustiziatributaria.gov.it/ricerca")
    time.sleep(3)

    # 1. SELEZIONA ANNO 2025
    anno = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//label[contains(text(),'Anno')]/parent::div//select")
    ))
    Select(anno).select_by_value("2025")

    # 2. SELEZIONA ESITO FAVOREVOLE
    esito = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//label[contains(text(),'Esito giudizio')]/parent::div//select")
    ))
    Select(esito).select_by_visible_text("Favorevole al contribuente")

    # 3. CLICCA RICERCA
    btn = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(text(),'Ricerca')]")
    ))
    btn.click()

    # 4. ATTENDI RISULTATI
    wait.until(EC.presence_of_element_located((By.XPATH, "//table")))

    # 5. CLICCA LA PRIMA SENTENZA
    first = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "(//a[contains(@href,'dettaglio')])[1]")
    ))
    first.click()

    # 6. ESTRAI IL TESTO
    blocco = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//div[contains(@class,'sentenza') or contains(@class,'container')]")
    ))

    testo = blocco.text.strip()
    driver.quit()

    if not testo:
        raise RuntimeError("Testo sentenza vuoto")

    today = dt.date.today().isoformat()

    # 7. GENERA HTML
    html = HTML_TPL.render(
        date=today,
        source=PDF_URL,
        text=testo[:200000]
    )

    # 8. SCRITTURA DEI FILE
    (OUT_DIR / "latest.html").write_text(html, encoding="utf-8")
    (OUT_DIR / f"sentenza_{today}.html").write_text(html, encoding="utf-8")

    print("✓ Sentenza pubblicata")
    print("→", f"{SITE_BASE}/sentenze/latest.html")

if __name__ == "__main__":
    main()
