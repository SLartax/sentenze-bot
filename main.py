import time
import datetime as dt
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from jinja2 import Template

# =========================
# OUTPUT
# =========================
OUT_DIR = Path("sentenze")
OUT_DIR.mkdir(exist_ok=True)

SITE_BASE = "https://slartax.github.io/sentenze-bot"

# =========================
# HTML TEMPLATE
# =========================
HTML_TPL = Template("""
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Riassunto sentenza</title>
</head>
<body>
<style>
body{font-family:system-ui;max-width:900px;margin:40px auto;padding:0 16px;line-height:1.6}
pre{white-space:pre-wrap;background:#f6f6f6;padding:16px;border-radius:12px;border:1px solid #ddd}
</style>

<h1>📄 Sentenza del giorno</h1>
<p><strong>Data:</strong> {{ date }}</p>

<pre>{{ text }}</pre>
</body>
</html>
""")

# =========================
# SELENIUM SETUP (HEADLESS)
# =========================
def make_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=opts)

# =========================
# MAIN SCRAPER
# =========================
def main():
    driver = make_driver()
    wait = WebDriverWait(driver, 30)

    print("Apro banca dati giurisprudenza…")
    driver.get("https://bancadatigiurisprudenza.giustiziatributaria.gov.it/ricerca")
    time.sleep(3)

    # ANNO 2025
    anno = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//label[contains(text(),'Anno')]/parent::div//select")
    ))
    Select(anno).select_by_value("2025")

    # ESITO FAVOREVOLE
    esito = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//label[contains(text(),'Esito giudizio')]/parent::div//select")
    ))
    Select(esito).select_by_visible_text("Favorevole al contribuente")

    # RICERCA
    btn = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(text(),'Ricerca')]")
    ))
    btn.click()

    # RISULTATI
    wait.until(EC.presence_of_element_located((By.XPATH, "//table")))

    # PRIMA SENTENZA
    first = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "(//a[contains(@href,'dettaglio')])[1]")
    ))
    first.click()

    # TESTO
    blocco = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//div[contains(@class,'sentenza') or contains(@class,'container')]")
    ))

    testo = blocco.text.strip()
    driver.quit()

    if not testo:
        raise RuntimeError("Testo sentenza vuoto")

    today = dt.date.today().isoformat()

    html = HTML_TPL.render(
        date=today,
        text=testo[:200000]
    )

    # =========================
    # SCRITTURE
    # =========================
    (OUT_DIR / "latest.html").write_text(html, encoding="utf-8")
    (OUT_DIR / f"sentenza_{today}.html").write_text(html, encoding="utf-8")

    print("✓ Sentenza pubblicata")
    print("→", f"{SITE_BASE}/sentenze/latest.html")

if __name__ == "__main__":
    main()
