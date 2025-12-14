# -*- coding: utf-8 -*-
"""
main.py - Sentenze Bot (GitHub Pages)
Output atteso (repo root):
  /sentenze/latest.html
  /sentenze/latest.pdf
  /sentenze/sentenza_YYYY-MM-DD.html
  /sentenze/sentenza_YYYY-MM-DD.pdf

La homepage (index.html) può fare fetch di:
  https://slartax.github.io/sentenze-bot/sentenze/latest.html
"""

import os
import sys
import time
import datetime as dt
from pathlib import Path

import requests
from pypdf import PdfReader
from jinja2 import Template

try:
    from zoneinfo import ZoneInfo
    ROME_TZ = ZoneInfo("Europe/Rome")
except Exception:
    ROME_TZ = None

# =========================
# CONFIG
# =========================
OUT_DIR = Path(os.getenv("OUT_DIR", "sentenze")).resolve()
OUT_DIR.mkdir(parents=True, exist_ok=True)

PDF_URL = os.getenv("PDF_URL", "").strip()
MAX_PAGES = int(os.getenv("MAX_PAGES", "30"))
MAX_CHARS = int(os.getenv("MAX_CHARS", "200000"))
TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "60"))
RETRIES = int(os.getenv("HTTP_RETRIES", "3"))

# Template: IMPORTANTISSIMO: mettiamo <style> DENTRO <body>
# perché tu prendi doc.body.innerHTML e lo inietti nella home.
HTML_TPL = Template("""
<div class="sentenza-wrap">
  <style>
    .sentenza-wrap{
      font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
      max-width:900px;
      margin:0 auto;
      line-height:1.6;
    }
    .sentenza-head{
      margin: 0 0 14px 0;
    }
    .sentenza-meta{
      color:#666;
      margin: 0 0 18px 0;
      font-size: 0.95em;
    }
    .sentenza-links a{
      display:inline-block;
      margin-right:12px;
    }
    pre.sentenza-text{
      white-space:pre-wrap;
      background:#f6f6f6;
      padding:16px;
      border-radius:12px;
      border:1px solid #e6e6e6;
      user-select:text;
      -webkit-user-select:text;
      -moz-user-select:text;
    }
  </style>

  <h2 class="sentenza-head">Riassunto sentenza</h2>
  <p class="sentenza-meta">
    <strong>Data:</strong> {{ date }} &nbsp;•&nbsp;
    <strong>Fonte:</strong> {{ source }}
  </p>

  <p class="sentenza-links">
    <a href="{{ pdf_public_path }}" target="_blank" rel="noopener">⬇️ PDF originale</a>
    <a href="{{ html_public_path }}" target="_blank" rel="noopener">🔗 Apri HTML</a>
  </p>

  {% if warning %}
    <p style="color:#b00020;"><strong>Nota:</strong> {{ warning }}</p>
  {% endif %}

  <pre class="sentenza-text">{{ text }}</pre>
</div>
""")

# =========================
# HELPERS
# =========================
def today_rome_iso() -> str:
    if ROME_TZ is None:
        return dt.date.today().isoformat()
    return dt.datetime.now(dt.timezone.utc).astimezone(ROME_TZ).date().isoformat()

def safe_write_bytes(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)

def safe_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    tmp.replace(path)

def is_probably_pdf(content: bytes) -> bool:
    # tollera whitespace iniziale
    head = content.lstrip()[:10]
    return head.startswith(b"%PDF")

def download_pdf(url: str, out_path: Path, retries: int = 3) -> bytes:
    if not url:
        raise SystemExit("Missing PDF_URL environment variable")

    headers = {
        "User-Agent": "Mozilla/5.0 (SentenzeBot/1.0)",
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
    }

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            preview = url[:80] + ("..." if len(url) > 80 else "")
            print(f"[download] Attempt {attempt}/{retries} -> {preview}")

            r = requests.get(url, headers=headers, timeout=TIMEOUT)
            r.raise_for_status()

            content = r.content or b""
            if not content:
                raise RuntimeError("Empty response body")

            # Verifica che sia davvero un PDF (molti siti rispondono HTML con 200)
            if not is_probably_pdf(content):
                ct = (r.headers.get("Content-Type") or "").lower()
                raise RuntimeError(f"Not a PDF (Content-Type={ct})")

            safe_write_bytes(out_path, content)
            print(f"[download] OK -> {out_path.name} ({len(content)} bytes)")
            return content

        except Exception as e:
            last_err = e
            print(f"[download] Error: {e}")
            if attempt < retries:
                sleep_s = 2 ** (attempt - 1)
                print(f"[download] Retry in {sleep_s}s...")
                time.sleep(sleep_s)

    raise SystemExit(f"Download failed after {retries} attempts: {last_err}")

def extract_text_from_pdf(pdf_path: Path, max_pages: int = 30) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        chunks = []
        for p in reader.pages[:max_pages]:
            chunks.append(p.extract_text() or "")
        return "\n".join(chunks).strip()
    except Exception as e:
        print(f"[extract] Errore estrazione PDF: {e}")
        return ""

# =========================
# MAIN
# =========================
def main() -> None:
    if not PDF_URL:
        raise SystemExit("Missing PDF_URL environment variable")

    today = today_rome_iso()

    pdf_day = OUT_DIR / f"sentenza_{today}.pdf"
    html_day = OUT_DIR / f"sentenza_{today}.html"

    latest_pdf = OUT_DIR / "latest.pdf"
    latest_html = OUT_DIR / "latest.html"

    # 1) Download PDF (se fallisce, NON tocchiamo latest.*)
    download_pdf(PDF_URL, pdf_day, retries=RETRIES)

    # 2) Extract testo
    text = extract_text_from_pdf(pdf_day, max_pages=MAX_PAGES)
    warning = ""
    if not text:
        # Pubblico comunque un HTML che avvisa (meglio di 404),
        # ma lascio il testo vuoto: spesso sono PDF “scansionati”.
        warning = "Testo non estraibile dal PDF (potrebbe essere una scansione)."

    text = (text or "").strip()
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n[... testo tagliato ...]"

    # 3) Costruisco percorsi pubblici relativi al sito (coerenti con Pages root)
    #    Questi link funzionano sia dentro home (embed) sia se apri latest.html diretto.
    pdf_public_path = f"./latest.pdf"
    html_public_path = f"./latest.html"

    # 4) Render HTML
    html = HTML_TPL.render(
        date=today,
        source=PDF_URL,
        pdf_public_path=pdf_public_path,
        html_public_path=html_public_path,
        warning=warning,
        text=text,
    )

    # 5) Salva versione giornaliera
    safe_write_text(html_day, html)

    # 6) Aggiorna latest.* SOLO ora che tutto è riuscito
    safe_write_text(latest_html, html)
    safe_write_bytes(latest_pdf, pdf_day.read_bytes())

    print("[OK] Generati:")
    print(f" - {html_day}")
    print(f" - {pdf_day}")
    print(f" - {latest_html}")
    print(f" - {latest_pdf}")

if __name__ == "__main__":
    main()
