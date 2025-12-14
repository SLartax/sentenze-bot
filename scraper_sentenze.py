# -*- coding: utf-8 -*-
"""
Scraper per Banca Dati Giurisprudenza Tributaria
Estrae l'ultima sentenza favorevole al contribuente
Ottimizzato per GitHub Actions (headless)
"""

import time
import os
import sys
from pathlib import Path

try:
    import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("Errore: librerie Selenium non installate")
    sys.exit(1)

def scrape_sentenza():
    """Scrape sentenza dall'ultima query favorevole al contribuente"""
    
    driver = None
    try:
        # Setup Chrome per GitHub Actions (headless)
        print("\n[1/5] Inizializzo browser...")
        
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        driver = uc.Chrome(options=options, version_main=None)
        wait = WebDriverWait(driver, 20)
        
        # Carica la pagina
        print("[2/5] Carico la banca dati tributaria...")
        driver.get("https://bancadatigiurisprudenza.giustiziatributaria.gov.it/ricerca")
        time.sleep(4)  # Aspetta il caricamento dinamico
        
        # Seleziona ANNO 2025
        print("[3/5] Applico filtri (Anno 2025, Favorevole)...")
        try:
            anno_select = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//label[contains(text(),'Anno')]/parent::div//select")
            ))
            Select(anno_select).select_by_value("2025")
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠ Avviso: Impossibile selezionare anno: {e}")
        
        # Seleziona ESITO = "Favorevole al contribuente"
        try:
            esito_select = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//label[contains(text(),'Esito')]/parent::div//select")
            ))
            Select(esito_select).select_by_visible_text("Favorevole al contribuente")
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠ Avviso: Impossibile selezionare esito: {e}")
        
        # Click RICERCA
        print("[4/5] Eseguo ricerca...")
        try:
            ricerca_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'Ricerca')]")
            ))
            driver.execute_script("arguments[0].scrollIntoView(true);", ricerca_btn)
            time.sleep(0.5)
            ricerca_btn.click()
            
            # Attendi risultati
            wait.until(EC.presence_of_element_located((By.XPATH, "//table")))
            time.sleep(2)
        except Exception as e:
            print(f"  ✗ Errore nella ricerca: {e}")
            return None
        
        # Apri la PRIMA sentenza
        print("[5/5] Estraggo il testo della sentenza...")
        try:
            first_link = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "(//a[contains(@href,'dettaglio')])[1]")
            ))
            first_link.click()
            time.sleep(3)  # Carica pagina dettaglio
        except Exception as e:
            print(f"  ✗ Errore: Nessuna sentenza trovata: {e}")
            return None
        
        # Estrai il testo
        try:
            # Prova diversi selettori per il testo
            text_selectors = [
                "//div[contains(@class,'sentenza')]//p",
                "//div[contains(@class,'contenuto-sentenza')]",
                "//div[contains(@id,'content')]",
                "//article",
                "//main"
            ]
            
            testo = None
            for selector in text_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        testo = "\n".join([el.text for el in elements if el.text])
                        if len(testo) > 100:
                            break
                except:
                    continue
            
            if not testo or len(testo) < 100:
                # Fallback: estrai tutto il body
                testo = driver.find_element(By.TAG_NAME, "body").text
            
            return testo[:200000]  # Limita a 200k caratteri
            
        except Exception as e:
            print(f"  ✗ Errore estrazione testo: {e}")
            return None
    
    except Exception as e:
        print(f"\n✗ ERRORE CRITICO: {e}")
        return None
    
    finally:
        if driver:
            driver.quit()

def generate_summary(testo):
    """Genera un riassunto semplice del testo (500 caratteri)"""
    if not testo or len(testo) < 100:
        return "Testo non disponibile"
    
    # Prendi i primi paragrafi significativi
    paragrafi = testo.split("\n\n")[:3]
    sommario = "\n\n".join(paragrafi)[:500] + "..."
    
    return sommario

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  ESTRAZIONE SENTENZA - BANCA DATI TRIBUTARIA")
    print("="*60)
    
    # Esegui scraping
    testo = scrape_sentenza()
    
    if testo:
        print("\n✓ Sentenza estratta con successo!")
        print(f"  Lunghezza: {len(testo)} caratteri")
        
        # Salva il testo completo
        out_dir = Path("public/sentenze")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        with open(out_dir / "sentenza_ultima.txt", "w", encoding="utf-8") as f:
            f.write(testo)
        
        # Genera e salva il riassunto
        riassunto = generate_summary(testo)
        with open(out_dir / "riassunto_ultima.txt", "w", encoding="utf-8") as f:
            f.write(riassunto)
        
        print(f"\n📄 File salvati in {out_dir}/")
        print(f"\n{'='*60}")
        print("RIASSUNTO:")
        print(f"{'='*60}")
        print(riassunto)
        print(f"{'='*60}\n")
        
        sys.exit(0)
    else:
        print("\n✗ Impossibile estrarre la sentenza")
        sys.exit(1)
