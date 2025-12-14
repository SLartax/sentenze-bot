#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple Selenium scraper for trial court sentenze"""

import os
import sys
from pathlib import Path
from datetime import date

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select, WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import undetected_chromedriver as uc
except ImportError as e:
    print(f"ERROR: Required libraries not found: {e}")
    print("Install with: pip install -r requirements.txt")
    sys.exit(1)

def main():
    """Main function"""
    print("[1/5] Initializing Chrome browser (headless)...")
    
    try:
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        
        driver = uc.Chrome(options=options, version_main=None)
        wait = WebDriverWait(driver, 20)
    except Exception as e:
        print(f"[X] Browser initialization failed: {e}")
        return False
    
    try:
        # Navigate
        print("[2/5] Loading Tribunale delle imposte database...")
        driver.get("https://bancadatigiurisprudenza.giustiziatributaria.gov.it/ricerca")
        
        # Wait for page to load
        from selenium.webdriver.common.by import By as BY
        wait.until(EC.presence_of_element_located((BY.TAG_NAME, "select")))
        
        print("[3/5] Applying filters (Year 2025, Favorable outcome)...")
        try:
            year_select = Select(driver.find_element(BY.XPATH, "//select[@name='anno']"))
            year_select.select_by_value("2025")
        except:
            pass
        
        # Search
        print("[4/5] Performing search...")
        try:
            search_btn = wait.until(
                EC.element_to_be_clickable((BY.XPATH, "//button[contains(text(),'Ricerca')]"))
            )
            search_btn.click()
            wait.until(EC.presence_of_element_located((BY.TAG_NAME, "table")))
        except Exception as e:
            print(f"[!] Search failed: {e}")
            driver.quit()
            return False
        
        # Extract first result
        print("[5/5] Extracting sentenza text...")
        try:
            first_link = driver.find_element(BY.XPATH, "(//a[contains(@href,'dettaglio')])[1]")
            first_link.click()
            
            # Wait for content
            import time
            time.sleep(2)
            
            # Try to extract text
            text = driver.find_element(BY.TAG_NAME, "body").text
            
            # Save
            out_dir = Path("public/sentenze")
            out_dir.mkdir(parents=True, exist_ok=True)
            
            today = date.today().isoformat()
            output_file = out_dir / f"sentenza_{today}.txt"
            output_file.write_text(text[:200000], encoding="utf-8")
            
            print(f"\n✓ Successfully extracted {len(text)} characters")
            print(f"✓ Saved to {output_file}")
            
            driver.quit()
            return True
            
        except Exception as e:
            print(f"[!] Extraction failed: {e}")
            driver.quit()
            return False
    
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
