from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin, urlparse, urldefrag, unquote
import re

START_URL = "https://developer.luxhub.com/products/"
OUTPUT_DIR = "scrape"
os.makedirs(OUTPUT_DIR, exist_ok=True)
visited = set()
to_visit = [START_URL]

def safe_filename(url):
    parsed = urlparse(url)
    path = unquote(parsed.path).strip("/").replace("/", "_") or "index"
    if parsed.query:
        query_decoded = unquote(parsed.query)
        query_safe = re.sub(r'[^a-zA-Z0-9_]', '_', query_decoded)
        path += "_" + query_safe
    safe_path = re.sub(r'[^a-zA-Z0-9_\-]', '_', path)
    return f"scraped_{safe_path}.html"

def save_html(content, filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(content)
    print(f"[HTML] Saved: {filepath}")

def normalize_url(url):
    return urldefrag(url.rstrip("/"))[0]

# Setup Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=chrome_options)

while to_visit:
    url = to_visit.pop(0)
    norm_url = normalize_url(url)
    if norm_url in visited:
        continue
    visited.add(norm_url)
    try:
        driver.get(url)
        time.sleep(3)  # Wait for JS to load
        soup = BeautifulSoup(driver.page_source, "html.parser")
        filename = safe_filename(url)
        save_html(soup.prettify(), filename)
        # Find all internal links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("mailto:") or href.startswith("javascript:"):
                continue
            full_url = urljoin(url, href)
            parsed_url = urlparse(full_url)
            if parsed_url.netloc == urlparse(START_URL).netloc:
                norm_full = normalize_url(full_url)
                if norm_full not in visited and norm_full not in to_visit:
                    to_visit.append(norm_full)
    except Exception as e:
        print(f"[ERROR] Failed to scrape: {url} | {e}")

driver.quit()
print("\n✅ Scraping completed. Total pages visited:", len(visited))