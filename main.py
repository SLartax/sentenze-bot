import os, datetime as dt, requests
from pypdf import PdfReader
from jinja2 import Template

OUT_DIR = os.path.join("public", "sentenze")
os.makedirs(OUT_DIR, exist_ok=True)

HTML_TPL = Template("""
<!doctype html><html lang="it"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Riassunto sentenza - {{ date }}</title>
<style>body{font-family:system-ui;max-width:900px;margin:40px auto;padding:0 16px;line-height:1.5}
pre{white-space:pre-wrap;background:#f6f6f6;padding:16px;border-radius:12px}</style>
</head><body>
<h1>Riassunto sentenza</h1>
<p>Data: {{ date }} • Fonte: {{ source }}</p>
<pre>{{ text }}</pre>
</body></html>
""")

PDF_URL = os.getenv("PDF_URL", "").strip()

def extract_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    chunks = []
    for p in reader.pages[:30]:
        t = p.extract_text() or ""
        chunks.append(t)
    return "\n".join(chunks).strip()

def main():
    if not PDF_URL:
        raise SystemExit("Missing PDF_URL env var")

    today = dt.date.today().isoformat()
    pdf_path = os.path.join(OUT_DIR, f"sentenza_{today}.pdf")

    try:
        r = requests.get(PDF_URL, timeout=60)
        r.raise_for_status()
        with open(pdf_path, "wb") as f:
            f.write(r.content)
    except Exception as e:
        print(f"Errore download PDF: {e}. Creando file vuoto.")
        with open(pdf_path, "wb") as f:
            f.write(b"")
    text = extract_text(pdf_path)
    html = HTML_TPL.render(date=today, source=PDF_URL, text=text[:200000])

    html_path = os.path.join(OUT_DIR, f"riassunto_{today}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # "latest" shortcuts
    with open(os.path.join(OUT_DIR, "latest.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(OUT_DIR, "latest.pdf"), "wb") as f:
        f.write(open(pdf_path, "rb").read())

    print("OK:", html_path, pdf_path)

if __name__ == "__main__":
    main()
