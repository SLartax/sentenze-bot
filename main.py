import os, datetime as dt, requests, sys, time
from pypdf import PdfReader
from jinja2 import Template

OUT_DIR = os.path.join("public", "sentenze")
os.makedirs(OUT_DIR, exist_ok=True)

HTML_TPL = Template("""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Riassunto sentenza - {{ date }}</title><style>body{font-family:system-ui;max-width:900px;margin:40px auto;padding:0 16px;line-height:1.5}pre{white-space:pre-wrap;background:#f6f6f6;padding:16px;border-radius:12px}</style></head><body><h1>Riassunto sentenza</h1><p>Data: {{ date }} • Fonte: {{ source }}</p><pre>{{ text }}</pre></body></html>""")

PDF_URL = os.getenv("PDF_URL", "").strip()

def extract_text(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        chunks = []
        for p in reader.pages[:30]:
            t = p.extract_text() or ""
            chunks.append(t)
        return "\n".join(chunks).strip()
    except Exception as e:
        print(f"Errore estrazione PDF: {e}")
        return ""

def download_pdf(url: str, output_path: str, max_retries: int = 3) -> bool:
    """Download PDF con retry logic e validazione."""
    if not url:
        raise SystemExit("PDF_URL env var is missing or empty")
    
    # Log prima 50 caratteri dell'URL per diagnostica (mascherare il resto)
    url_preview = url[:50] + ("..." if len(url) > 50 else "")
    print(f"Attempting to download PDF from: {url_preview}")
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Download attempt {attempt}/{max_retries}...")
            r = requests.get(url, timeout=60)
            r.raise_for_status()  # Raise HTTPError for bad status codes
            
            if not r.content:
                raise Exception("Ricevuto contenuto vuoto dal server")
            
            with open(output_path, "wb") as f:
                f.write(r.content)
            
            file_size = os.path.getsize(output_path)
            print(f"Successfully downloaded PDF ({file_size} bytes)")
            return True
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error {e.response.status_code}: {e.response.reason}"
            print(f"[Attempt {attempt}] {error_msg}")
            
            if e.response.status_code == 404:
                print("PDF not found (404). Check if URL is correct.")
                return False
            elif attempt < max_retries:
                wait_time = 2 ** (attempt - 1)  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        except requests.exceptions.RequestException as e:
            print(f"[Attempt {attempt}] Connection error: {e}")
            if attempt < max_retries:
                wait_time = 2 ** (attempt - 1)
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        except Exception as e:
            print(f"[Attempt {attempt}] Unexpected error: {e}")
            return False
    
    print(f"Failed to download PDF after {max_retries} attempts")
    return False

def main():
    if not PDF_URL:
        raise SystemExit("Missing PDF_URL environment variable")
    
    today = dt.date.today().isoformat()
    pdf_path = os.path.join(OUT_DIR, f"sentenza_{today}.pdf")
    
    # Download con retry logic
    if not download_pdf(PDF_URL, pdf_path):
        # Clean up empty file if it exists
        try:
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) == 0:
                os.remove(pdf_path)
        except Exception:
            pass
        sys.exit(1)
    
    # Extract and generate HTML
    text = extract_text(pdf_path)
    html = HTML_TPL.render(date=today, source=PDF_URL[:50] + "..." if len(PDF_URL) > 50 else PDF_URL, text=text[:200000])
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
