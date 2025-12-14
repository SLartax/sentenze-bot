import os
import sys
import time
import datetime as dt
import requests
from pathlib import Path
from pypdf import PdfReader
from jinja2 import Template

# =========================
# CONFIG
# =========================
OUT_DIR = Path("sentenze")          # <<< ROOT, NON public/
OUT_DIR.mkdir(exist_ok=True)

PDF_URL = os.getenv("PDF_URL", "").strip()
MAX_PAGES = 30

HTML_TPL = Template("""
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Riassunto sentenza – {{ date }}</title>
  <style>
    body {
      font-family: system-ui;
      max-width: 900px;
      margin: 40px auto;
      padding: 0 16px;
      line-height: 1.6;
    }
    pre {
      white-space: pre-wrap;
      background: #f6f6f6;
      padding: 16px;
      border-radius: 12px;
    }
  </style>
</head>
<body>
  <h1>Riassunto sentenza</h1>
  <p><strong>Data:</strong> {{ date }}<br>
     <strong>Fonte:</strong> {{ source }}</p>
  <pre>{{ text }}</pre>
</body>
</html>
""")

# =========================
# HELPERS
# =========================
def extract_text(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        chunks = []
        for p in reader.pages[:MAX_PAGES]:
            chunks.append(p.extract_text() or "")
        return "\n".join(chunks).strip()
    except Exception as e:
        print(f"Errore estrazione PDF: {e}")
        return ""

def download_pdf(url: str, output_path: Path, retries: int = 3) -> bool:
    if not url:
        raise SystemExit("PDF_URL env var is missing")

    for attempt in range(1, retries + 1):
        try:
            print(f"Download tentativo {attempt}/{retries}")
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            output_path.write_bytes(r.content)
            return True
        except Exception as e:
            print(f"Errore download: {e}")
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))
    return False

# =========================
# MAIN
# =========================
def main():
    if not PDF_URL:
        raise SystemExit("Missing PDF_URL")

    today = dt.date.today().isoformat()
    pdf_path = OUT_DIR / f"sentenza_{today}.pdf"

    if not download_pdf(PDF_URL, pdf_path):
        raise SystemExit("Download PDF fallito")

    text = extract_text(pdf_path)
    if not text:
        raise SystemExit("Testo PDF vuoto")

    html = HTML_TPL.render(
        date=today,
        source=PDF_URL,
        text=text[:200_000]
    )

    # versioni HTML
    (OUT_DIR / f"sentenza_{today}.html").write_text(html, encoding="utf-8")
    (OUT_DIR / "latest.html").write_text(html, encoding="utf-8")

    # versione PDF latest
    (OUT_DIR / "latest.pdf").write_bytes(pdf_path.read_bytes())

    print("✓ Generati:")
    print("  - sentenze/latest.html")
    print("  - sentenze/latest.pdf")

if __name__ == "__main__":
    main()

