import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse

# URL of the website to scrape
url = "https://grantgiverfund.com/cms"

def save_html(content, filename):
    with open(filename, "w", encoding="utf-8") as file:
        file.write(content)
    print(f"HTML content saved to {filename}")

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"Error fetching the website: {e}")
    exit()

soup = BeautifulSoup(response.text, "html.parser")
html_content = soup.prettify()
save_html(html_content, "website.html")

# Find all href links
links = set()
for a_tag in soup.find_all("a", href=True):
    href = a_tag["href"]
    # Make absolute URL
    full_url = urljoin(url, href)
    # Only scrape links from the same domain
    if urlparse(full_url).netloc == urlparse(url).netloc:
        links.add(full_url)

# Scrape each link and save to a separate file
for idx, link in enumerate(links, 1):
    try:
        resp = requests.get(link, timeout=10)
        resp.raise_for_status()
        page_soup = BeautifulSoup(resp.text, "html.parser")
        page_html = page_soup.prettify()
        # Create a safe filename
        parsed = urlparse(link)
        path = parsed.path.strip("/").replace("/", "_") or "index"
        filename = f"scraped_{path}.html"
        save_html(page_html, filename)
    except Exception as e:
        print(f"Failed to scrape {link}: {e}")




# import requests
# from bs4 import BeautifulSoup
# import os

# # URL of the website to scrape
# url = "https://www.zemplerbank.com/api-developer/"  # Replace with the target website URL

# # Send a GET request to the website
# try:
#     response = requests.get(url, timeout=10)
#     response.raise_for_status()  # Check for HTTP errors
# except requests.exceptions.RequestException as e:
#     print(f"Error fetching the website: {e}")
#     exit()

# # Parse the HTML content using BeautifulSoup
# soup = BeautifulSoup(response.text, "html.parser")

# # Get the prettified HTML
# html_content = soup.prettify()

# # Define the output file path
# output_file = "website.html"

# # Save the HTML to a file
# try:
#     with open(output_file, "w", encoding="utf-8") as file:
#         file.write(html_content)
#     print(f"HTML content saved to {output_file}")
# except IOError as e:
#     print(f"Error saving the file: {e}")