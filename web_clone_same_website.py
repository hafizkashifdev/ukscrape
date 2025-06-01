import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse, quote

# Base URL to scrape
url = "https://developers.worldfirst.com/docs/alipay-worldfirst/documentation/apis"
base_domain = urlparse(url).netloc

# Headers to mimic a browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Create main folder
os.makedirs(base_domain, exist_ok=True)

def safe_filename(parsed):
    path = parsed.path.strip("/").replace("/", "_") or "index"
    if parsed.query:
        path += "_" + quote(parsed.query, safe="")
    if parsed.fragment:
        path += "_" + quote(parsed.fragment, safe="")
    return f"scraped_{path}.html"

def save_html(content, folder, filename):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(content)
    print(f"✅ Saved: {filepath}")

# --- STEP 1: Scrape and save base page ---
try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    save_html(soup.prettify(), base_domain, "website.html")
except Exception as e:
    print(f"❌ Failed to fetch base URL: {e}")
    exit()

# --- STEP 2: Find and classify links ---
internal_links = set()
external_links = set()

for a_tag in soup.find_all("a", href=True):
    href = a_tag["href"].strip()
    if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
        continue
    full_url = urljoin(url, href)
    parsed = urlparse(full_url)
    if not parsed.scheme.startswith("http"):
        continue
    if parsed.netloc == base_domain:
        internal_links.add(full_url)
    else:
        external_links.add(full_url)

# --- STEP 3: Function to scrape and save a link ---
def scrape_and_save(link, folder):
    try:
        resp = requests.get(link, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        parsed = urlparse(link)
        filename = safe_filename(parsed)
        save_html(soup.prettify(), folder, filename)
    except Exception as e:
        print(f"❌ Failed to scrape {link}: {e}")

# --- STEP 4: Scrape internal links ---
print(f"\n🔍 Scraping {len(internal_links)} internal links...")
for link in sorted(internal_links):
    scrape_and_save(link, base_domain)

# --- STEP 5: Scrape external links into separate folders ---
print(f"\n🌐 Scraping {len(external_links)} external links...")
for link in sorted(external_links):
    ext_domain = urlparse(link).netloc or "external"
    scrape_and_save(link, ext_domain)
