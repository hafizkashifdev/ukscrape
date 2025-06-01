import os
import time
from urllib.parse import urljoin, urlparse, quote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# === CONFIG ===
BASE_URL = "https://developers.worldfirst.com/docs/alipay-worldfirst/documentation/apis"
PROXY = None
HEADLESS = True
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
main_domain = urlparse(BASE_URL).netloc

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
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Saved: {filepath}")

def save_screenshot(driver, folder, filename):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    driver.save_screenshot(filepath)
    print(f"📸 Screenshot saved: {filepath}")

def allowed_by_robots(url):
    from urllib.robotparser import RobotFileParser
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except:
        print("⚠️ Could not read robots.txt, proceeding with caution.")
        return True

def setup_driver():
    chrome_options = webdriver.ChromeOptions()
    if HEADLESS:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    if PROXY:
        chrome_options.add_argument(f"--proxy-server={PROXY}")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_window_size(1920, 1080)  # Force desktop/PC mode
    return driver

def open_all_dropdowns(driver):
    try:
        triangles = driver.find_elements(By.CSS_SELECTOR, ".style-module_triangle__N-gXA")
        for triangle in triangles:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", triangle)
                triangle.click()
                time.sleep(0.2)
            except Exception:
                continue
    except Exception as e:
        print("⚠️ Could not open all dropdowns:", e)

def wait_for_content(driver, timeout=20):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "main, .index-module_main__2B9Eq, .index-module_content__6p5ch"))
        )
        time.sleep(3)  # Give React/SPA time to render
    except Exception as e:
        print("⚠️ Content may not be fully loaded:", e)

def handle_cookie_banner(driver):
    try:
        cookie_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
        )
        cookie_btn.click()
        print("🍪 Cookie banner accepted.")
    except:
        pass  # Cookie banner not present or already accepted

def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    # Remove script and style tags for cleaner output
    for tag in soup(["script", "style"]):
        tag.decompose()
    # Prettify the HTML for readability
    return soup.prettify()

def scrape_and_save(driver, link, folder):
    try:
        if not allowed_by_robots(link):
            print(f"⛔ Skipped due to robots.txt: {link}")
            return
        driver.get(link)
        driver.set_window_size(1920, 1080)
        handle_cookie_banner(driver)
        open_all_dropdowns(driver)
        wait_for_content(driver)
        raw_html = driver.page_source
        pretty_html = clean_html(raw_html)
        filename = safe_filename(urlparse(link))
        save_html(pretty_html, folder, filename)
        screenshot_name = filename.replace(".html", ".png")
        save_screenshot(driver, folder, screenshot_name)
    except Exception as e:
        print(f"❌ Failed to scrape {link}: {e}")

# === MAIN SCRIPT ===
driver = setup_driver()
scrape_and_save(driver, BASE_URL, main_domain)

internal_links = set()
external_links = set()

driver.get(BASE_URL)
wait_for_content(driver)
soup = BeautifulSoup(driver.page_source, "html.parser")

for tag in soup.find_all("a", href=True):
    href = tag["href"].strip()
    if href.startswith(("#", "mailto:", "tel:", "javascript:")):
        continue
    full_url = urljoin(BASE_URL, href)
    parsed = urlparse(full_url)
    if parsed.netloc == main_domain:
        internal_links.add(full_url)
    elif parsed.scheme.startswith("http"):
        external_links.add(full_url)

print(f"\n🔍 Scraping {len(internal_links)} internal links...")
for link in sorted(internal_links):
    scrape_and_save(driver, link, main_domain)

print(f"\n🌍 Scraping {len(external_links)} external links...")
for link in sorted(external_links):
    ext_domain = urlparse(link).netloc or "external"
    scrape_and_save(driver, link, ext_domain)

driver.quit()
print("\n✅ All scraping complete.")