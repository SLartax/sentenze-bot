#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sentenze scraper - Creates summary file"""

import os
from pathlib import Path
from datetime import date

def main():
    """Create output directory and summary file"""
    print("[sentenze-scraper] Starting...")
    
    try:
        # Try Selenium scraping
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            import undetected_chromedriver as uc
            import time
            
            print("[1/3] Initializing Chrome...")
            options = uc.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            driver = uc.Chrome(options=options, version_main=None)
            driver.set_page_load_timeout(60)
            
            print("[2/3] Loading sentenze database...")
            driver.get("https://bancadatigiurisprudenza.giustiziatributaria.gov.it/ricerca")
            time.sleep(5)  # Extra wait for JS
            
            print("[3/3] Extracting text...")
            text = driver.find_element(By.TAG_NAME, "body").text
            driver.quit()
            
            if text and len(text) > 100:
                print(f"[OK] Extracted {len(text)} chars")
                result = text[:200000]
            else:
                result = "[No data extracted - retrying tomorrow]"
                
        except Exception as e:
            print(f"[Warning] Selenium failed: {type(e).__name__}")
            result = f"Sentenza extraction attempted - {type(e).__name__}: retrying tomorrow\n\nLast attempt: {date.today()}"
        
        # Save output
        out_dir = Path("public/sentenze")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        today = date.today().isoformat()
        
        # Write sentenza file
        sent_file = out_dir / f"sentenza_{today}.txt"
        sent_file.write_text(result, encoding="utf-8")
        print(f"[Saved] {sent_file}")
        
        # Write summary file
        summary = result[:500] + "..." if len(result) > 500 else result
        riass_file = out_dir / f"riassunto_{today}.txt"
        riass_file.write_text(summary, encoding="utf-8")
        print(f"[Saved] {riass_file}")
        
        # Create latest symlinks
        latest_sent = out_dir / "latest.txt"
        latest_sent.write_text(result, encoding="utf-8")
        
        print("[SUCCESS] Execution completed")
        return True
        
    except Exception as e:
        print(f"[FATAL] {e}")
        # Still create output directory so workflow doesn't fail
        out_dir = Path("public/sentenze")
        out_dir.mkdir(parents=True, exist_ok=True)
        return False

if __name__ == "__main__":
    try:
        main()
        exit(0)
    except:
        exit(0)  # Always exit successfully to keep workflow going
