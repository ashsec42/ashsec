import argparse
import os
import requests
from typing import List

# --- Configuration Constants ---
DEFAULT_OUTPUT_FILE = "ashsec.m3u"
DEFAULT_TIMEOUT = 30 

# Headers to mimic a real web browser (Fixes 403 Forbidden errors)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

def fetch_m3u_content(url: str, timeout: int) -> List[str]:
    """
    Fetches M3U content and cleans invisible characters that break Android apps.
    """
    try:
        response = requests.get(url, timeout=timeout, headers=BROWSER_HEADERS)
        response.raise_for_status()
        response.encoding = 'utf-8' # Force UTF-8 encoding
        
        # KEY FIX: Remove BOM (Byte Order Mark) - \ufeff
        # This invisible character often makes Android apps stop reading the file.
        content = response.text.replace('\ufeff', '')
        
        lines = content.splitlines()
        
        if len(lines) < 2:
            print(f"⚠️ Warning: Content from {url} is too short.")
            return []
            
        print(f"✅ Success: Fetched {len(lines)} lines from {url}")
        return lines

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching {url}: {e}")
    
    return []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    m3u_links = os.environ.get('M3U_LINKS')
    if not m3u_links:
        print("❌ Error: M3U_LINKS not set.")
        return

    urls = [link.strip() for link in m3u
