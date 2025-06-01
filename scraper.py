import requests
from bs4 import BeautifulSoup
import os

# URL of the website to scrape
url = "https://docs.adyen.com/api-explorer"  # Replace with your target URL

# Set headers to mimic a browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Send a GET request to the website
try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    print(f"Status Code: {response.status_code}")
    print(f"Final URL: {response.url}")
    print(f"Response Content (first 500 chars):\n{response.text[:500]}")
except requests.exceptions.RequestException as e:
    print(f"Error fetching the website: {e}")
    exit()

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(response.text, "lxml")  # Try 'lxml' parser
html_content = soup.prettify()
print(f"Parsed HTML Length: {len(html_content)}")

# Define the output file path
output_file = os.path.join(os.getcwd(), "website.html")

# Save the HTML to a file
try:
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(html_content)
    print(f"HTML content saved to {output_file}")
except IOError as e:
    print(f"Error saving the file: {e}")