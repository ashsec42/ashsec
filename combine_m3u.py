import argparse
import os
import requests
from typing import List

# --- Configuration Constants ---
DEFAULT_OUTPUT_FILE = "ashsec.m3u"
DEFAULT_TIMEOUT = 15

def fetch_m3u_content(url: str, timeout: int) -> List[str]:
    """
    Fetches M3U content from a URL, handling network errors gracefully.
    
    Args:
        url: The remote URL of the M3U playlist.
        timeout: The maximum time in seconds to wait for the response.

    Returns:
        A list of content lines if successful, otherwise an empty list.
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        print(f"✅ Success: Fetched content from {url}")
        # Note: Using response.text.splitlines() handles different line endings (LF, CRLF)
        return response.text.splitlines()
    except requests.exceptions.Timeout:
        print(f"❌ Error: Request timed out fetching {url} after {timeout}s.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: Failed to fetch {url}: {e}")
    return []

# The cleanup function is kept purely for stripping whitespace and remains inactive against content.
def clean_stream_url(url_line: str) -> str:
    """Strips leading/trailing whitespace from a line."""
    return url_line.strip()

def main():
    """Main function to extract and combine M3U playlist content verbatim."""
    parser = argparse.ArgumentParser(description="Combines multiple M3U playlists verbatim, preserving all original content (except duplicate headers).")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_FILE, help="Output file path.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP fetch timeout in seconds.")
    args = parser.parse_args()

    m3u_links = os.environ.get('M3U_LINKS')
    if not m3u_links:
        print("❌ Error: M3U_LINKS environment variable not set. Please set the GitHub Secret or local ENV variable.")
        return

    urls = [link.strip() for link in m3u_links.splitlines() if link.strip()]
    if not urls:
        print("❌ Error: M3U_LINKS is set but contains no valid URLs.")
        return

    # Combined list will be populated with content lines
    combined_lines = [] 
    has_header = False # Flag to ensure only one #EXTM3U is kept

    for url in urls:
        print(f"\n⏳ Processing {url}...")
        lines = fetch_m3u_content(url, args.timeout)
        
        if not lines:
            continue
            
        for line in lines:
            stripped_line = line.strip()
            
            # 1. Handle the #EXTM3U header only once
            if stripped_line.startswith('#EXTM3U'):
                if not has_header:
                    combined_lines.append(stripped_line)
                    has_header = True
                continue # Skip all other #EXTM3U headers

            # 2. Append all other lines exactly as they are (after stripping whitespace)
            if stripped_line:
                combined_lines.append(stripped_line)

    # Manual enforcement of header if no source provided one
    if not has_header:
        combined_lines.insert(0, "#EXTM3U")
    
    # 3. Final Output
    if len(combined_lines) > 1:
        # Save file with UTF-8 encoding and a final newline
        with open(args.output, "w", encoding="utf-8") as f:
            f.write('\n'.join(combined_lines) + '\n') 
        
        print("\n" + "="*50)
        print(f"🎉 Final Verbatim Playlist Created!")
        print(f"File: {args.output}")
        # Subtracting 1 for the mandatory #EXTM3U header
        print(f"Total content lines added: {len(combined_lines) - 1}")
        print("="*50)
    else:
        print(f"\n⚠️ No valid content was successfully processed. {args.output} was not created or updated.")

if __name__ == "__main__":
    main()
