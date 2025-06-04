from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException,
    NoSuchElementException,
)
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin, urlparse, urldefrag, unquote
import re
import uuid

START_URL = "https://banfico.com/developers/#devallportals"
OUTPUT_DIR = "banfico_scraped_html"
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

def expand_swagger_elements(driver):
    """Expand all Swagger UI dropdowns and 'Try it out' buttons, return new links."""
    new_links = set()
    try:
        # Wait for Swagger UI to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "opblock"))
        )
        
        # Find all operation blocks
        operation_blocks = driver.find_elements(By.CLASS_NAME, "opblock")
        print(f"[INFO] Found {len(operation_blocks)} operation blocks to expand")
        
        for block in operation_blocks:
            try:
                # Check if block is already expanded
                is_expanded = block.get_attribute("class").find("is-open") != -1
                if not is_expanded:
                    # Click to expand
                    header = block.find_element(By.CLASS_NAME, "opblock-summary")
                    header.click()
                    time.sleep(0.5)  # Wait for animation
                    
                    # Click 'Try it out' if present
                    try:
                        try_it_out = block.find_element(By.XPATH, ".//button[contains(text(), 'Try it out')]")
                        try_it_out.click()
                        time.sleep(1)  # Wait for parameters to load
                    except NoSuchElementException:
                        print(f"[INFO] No 'Try it out' button in block")
                    
                    # Re-parse page for new links after expansion
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag["href"]
                        if href.startswith("mailto:") or href.startswith("javascript:"):
                            continue
                        full_url = urljoin(driver.current_url, href)
                        parsed_url = urlparse(full_url)
                        if parsed_url.netloc == urlparse(START_URL).netloc:
                            norm_full = normalize_url(full_url)
                            if norm_full not in visited and norm_full not in to_visit:
                                new_links.add(norm_full)
                                
                # Ensure content is loaded
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "opblock-body"))
                )
            except StaleElementReferenceException:
                print("[WARNING] Stale element encountered, re-fetching blocks")
                operation_blocks = driver.find_elements(By.CLASS_NAME, "opblock")
                continue
            except Exception as e:
                print(f"[WARNING] Failed to expand block: {e}")
                
        return new_links
    except TimeoutException:
        print("[WARNING] Timeout waiting for Swagger UI elements")
        return new_links
    except Exception as e:
        print(f"[ERROR] Error expanding Swagger elements: {e}")
        return new_links

# Setup Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=chrome_options)

try:
    while to_visit:
        url = to_visit.pop(0)
        norm_url = normalize_url(url)
        if norm_url in visited:
            print(f"[INFO] Skipping visited URL: {url}")
            continue
        visited.add(norm_url)
        print(f"[INFO] Scraping: {url}")
        
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                driver.get(url)
                # Wait for page to load
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Expand Swagger UI elements and collect new links
                new_links = expand_swagger_elements(driver)
                
                # Get page source after interactions
                soup = BeautifulSoup(driver.page_source, "html.parser")
                filename = safe_filename(url)
                save_html(soup.prettify(), filename)
                
                # Collect all links from the page
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
                
                # Add new links from Swagger expansions
                for link in new_links:
                    if link not in visited and link not in to_visit:
                        to_visit.append(link)
                
                break  # Exit retry loop on success
                
            except TimeoutException:
                retry_count += 1
                print(f"[ERROR] Timeout loading page {url}, retry {retry_count}/{max_retries}")
                time.sleep(2)
                if retry_count == max_retries:
                    print(f"[ERROR] Failed to load {url} after {max_retries} retries")
            except WebDriverException as e:
                retry_count += 1
                print(f"[ERROR] WebDriver error for {url}: {e}, retry {retry_count}/{max_retries}")
                time.sleep(2)
                if retry_count == max_retries:
                    print(f"[ERROR] Failed to load {url} after {max_retries} retries")
            except Exception as e:
                print(f"[ERROR] Failed to scrape {url}: {e}")
                break
                
finally:
    driver.quit()
    print("\n✅ Scraping completed. Total pages visited:", len(visited))