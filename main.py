import os
import sys
import time
import datetime as dt
from pathlib import Path

import requests
from pypdf import PdfReader
from jinja2 import Template

# =========================
# OUTPUT (ROOT del repo)
# =========================
OUT_DIR = Path("sentenze")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PDF_URL = os.getenv("PDF_URL", "").strip()

HTML_TPL = Template("""
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Riassunto sentenza - {{ date }}</title>
  <style>
    body{font-family:system-ui;max-width:900px;margin:40px auto;padding:0 16px;line-height:1.6}
    pre{white-space:pre-wrap;background:#f6f6f6;padding:16px;border-radius:12px;border:1px solid #e6e6e6}
  </style>
</head>
<body>
  <h1>Riassunto sentenza</h1>
  <p><strong>Data:</strong> {{ date }} • <strong>Fonte:</strong> {{ source }}</p>
  <p>
    <a href="./latest.pdf" target="_blank" rel="noopener">⬇️ PDF originale</a>
  </p>
  {% if warning %}
    <p style="color:#b00020;"><strong>Nota:</strong> {{ warning }}</p>
  {% endif %}
  <pre>{{ text }}</pre>
</body>
</html>
""")

def extract_text(pdf_path: Path, max_pages: int = 30) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        chunks = []
        for p in reader.pages[:max_pages]:
            chunks.append(p.extract_text() or "")
        return "\n".join(chunks).strip()
    except Exception as e:
        print(f"Errore estrazione PDF: {e}")
        return ""

def is_probably_pdf(content: bytes) -> bool:
    return content.lstrip().startswith(b"%PDF")

def download_pdf(url: str, output_path: Path, max_retries: int = 3) -> bool:
    if not url:
        raise SystemExit("PDF_URL env var is missing or empty")

    url_preview = url[:80] + ("..." if len(url) > 80 else "")
    print(f"Download PDF da: {url_preview}")

    headers = {"User-Agent": "Mozilla/5.0"}

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Tentativo {attempt}/{max_retries}...")
            r = requests.get(url, headers=headers, timeout=60)
            r.raise_for_status()

            if not r.content:
                raise RuntimeError("Contenuto vuoto")

            if not is_probably_pdf(r.content):
                ct = (r.headers.get("Content-Type") or "").lower()
                raise RuntimeError(f"Risposta non-PDF (Content-Type={ct})")

            output_path.write_bytes(r.content)
            print(f"OK PDF salvato: {output_path} ({output_path.stat().st_size} bytes)")
            return True

        except Exception as e:
            print(f"Errore: {e}")
            if attempt < max_retries:
                wait_time = 2 ** (attempt - 1)
                print(f"Retry in {wait_time}s...")
                time.sleep(wait_time)

    return False

def main():
    if not PDF_URL:
        raise SystemExit("Missing PDF_URL environment variable")

    today = dt.date.today().isoformat()

    pdf_day = OUT_DIR / f"sentenza_{today}.pdf"
    html_day = OUT_DIR / f"riassunto_{today}.html"

    latest_html = OUT_DIR / "latest.html"
    latest_pdf = OUT_DIR / "latest.pdf"

    # 1) Download
    if not download_pdf(PDF_URL, pdf_day):
        sys.exit(1)

    # 2) Extract
    text = extract_text(pdf_day, max_pages=30)
    warning = ""
    if not text:
        warning = "Testo non estraibile dal PDF (probabile scansione)."

    text = (text or "").strip()
    if len(text) > 200_000:
        text = text[:200_000] + "\n\n[... testo tagliato ...]"

    html = HTML_TPL.render(
        date=today,
        source=PDF_URL,
        text=text,
        warning=warning
    )

    # 3) Salvataggi
    html_day.write_text(html, encoding="utf-8")
    latest_html.write_text(html, encoding="utf-8")
    latest_pdf.write_bytes(pdf_day.read_bytes())

    print("✓ Generati:")
    print("  -", html_day)
    print("  -", pdf_day)
    print("  -", latest_html)
    print("  -", latest_pdf)

if __name__ == "__main__":
    main()
