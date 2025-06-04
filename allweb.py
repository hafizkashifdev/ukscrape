import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin, urlparse, urldefrag, unquote
from collections import deque
import urllib.robotparser
import re

# === CONFIGURATION ===
START_URL = "https://www.investec.com/en_int.html"
OUTPUT_DIR = "limited"
BATCH_SIZE = 10
DELAY_SECONDS = 1
BYPASS_ROBOTS_TXT = True  # Set to False to honor robots.txt

# === SETUP ===
os.makedirs(OUTPUT_DIR, exist_ok=True)
visited = set()
to_visit = deque()
saved_pages = []

# === SESSION SETUP ===
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
})

# === SAFE FILENAME CREATOR ===
def safe_filename(url):
    """
    Create a safe filename from URL by decoding and replacing unsafe chars.
    """
    parsed = urlparse(url)
    # Decode URL-encoded path and query
    path = unquote(parsed.path).strip("/").replace("/", "_") or "index"
    if parsed.query:
        query_decoded = unquote(parsed.query)
        # Replace anything not alphanumeric or underscore with underscore
        query_safe = re.sub(r'[^a-zA-Z0-9_]', '_', query_decoded)
        path += "_" + query_safe

    # Replace any leftover unsafe chars in path (like {, }, %, ?, &, =) with underscore
    safe_path = re.sub(r'[^a-zA-Z0-9_\-]', '_', path)

    return f"scraped_{safe_path}.html"

# === SAVE HTML TO FILE ===
def save_html(content, filename, page_url):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(content)
    print(f"[HTML] Saved: {filepath}")
    saved_pages.append((filename, page_url))

# === DEDUPLICATE URL ===
def normalize_url(url):
    return urldefrag(url.rstrip("/"))[0]

# === AUTO-CLICK COOKIES (simulated) ===
def handle_cookie_popup(soup):
    cookie_buttons = soup.find_all("button")
    for button in cookie_buttons:
        if button.text.strip().lower() in ["accept", "i agree", "allow all"]:
            print("🍪 Cookie consent found and accepted (simulated).")
            break

# === SCRAPE A SINGLE PAGE ===
def scrape_page(link, base_domain):
    normalized = normalize_url(link)
    if normalized in visited:
        return
    visited.add(normalized)

    time.sleep(DELAY_SECONDS)
    try:
        resp = session.get(link, timeout=10)
        resp.raise_for_status()
        page_soup = BeautifulSoup(resp.text, "html.parser")

        handle_cookie_popup(page_soup)

        filename = safe_filename(link)
        save_html(page_soup.prettify(), filename, link)

        # Find all <a> tags with href only
        for a_tag in page_soup.find_all("a", href=True):
            href = a_tag.get("href")

            if not href:
                continue
            # Ignore mailto: and javascript: links
            if href.startswith("mailto:") or href.startswith("javascript:"):
                continue

            full_url = urljoin(link, href)
            normalized_url = normalize_url(full_url)
            parsed_url = urlparse(normalized_url)

            # Only enqueue URLs on the same domain and not visited
            if parsed_url.netloc == base_domain and normalized_url not in visited:
                to_visit.append(normalized_url)

    except Exception as e:
        print(f"[ERROR] Failed to scrape: {link} | {e}")

# === ROBOTS.TXT CHECK ===
def check_robots_txt(base_url):
    if BYPASS_ROBOTS_TXT:
        print("[⚠️] Bypassing robots.txt (not recommended for production scraping).")
        return True  # Allow scraping

    rp = urllib.robotparser.RobotFileParser()
    robots_url = urljoin(base_url, "/robots.txt")
    rp.set_url(robots_url)
    try:
        rp.read()
        allowed = rp.can_fetch("*", base_url)
        if not allowed:
            print(f"[BLOCKED] robots.txt disallows: {base_url}")
        return allowed
    except Exception as e:
        print(f"[WARNING] Couldn't read robots.txt: {e}")
        return False  # Fail safe: deny if error

# === GENERATE INDEX.HTML ===
def generate_index():
    index_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("<html><head><title>Scraped Pages Index</title></head><body>\n")
        f.write("<h1>Scraped Pages</h1>\n<ul>\n")
        for filename, page_url in saved_pages:
            f.write(f'<li><a href="{filename}" target="_blank">{page_url}</a></li>\n')
        f.write("</ul>\n</body></html>")
    print(f"\n📄 Index file created: {index_path}")

# === MAIN CONTROLLER ===
def run_scraper():
    base_domain = urlparse(START_URL).netloc
    if not check_robots_txt(START_URL):
        print("Aborting: Disallowed by robots.txt")
        return

    to_visit.append(START_URL)

    while to_visit:
        batch = []
        while to_visit and len(batch) < BATCH_SIZE:
            url = to_visit.popleft()
            if url not in visited:
                batch.append(url)

        print(f"\n🔄 Scraping batch of {len(batch)} pages...\n")
        for link in batch:
            scrape_page(link, base_domain)

    generate_index()
    print("\n✅ Scraping completed. Total pages visited:", len(visited))

# === ENTRY POINT ===
if __name__ == "__main__":
    run_scraper()