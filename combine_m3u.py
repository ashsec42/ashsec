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

def clean_stream_url(url_line: str) -> str:
    """
    CLEANUP LOGIC: Removes pipe-separated parameters from a stream URL line.
    Example: 'http://stream.url|tvg-id="123"' becomes 'http://stream.url'
    """
    if '|' in url_line:
        # Split at the first pipe and return only the URL part
        cleaned_url = url_line.split('|')[0].strip()
        return cleaned_url
    return url_line.strip()

def main():
    """Main function to combine, clean, and format multiple remote M3U playlists."""
    parser = argparse.ArgumentParser(description="Combines multiple M3U playlists with cleanup and standardized formatting.")
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

    # GUARANTEED HEADER: Start the combined list with the mandatory header
    combined_lines = ["#EXTM3U"]
    processed_stream_count = 0

    for url in urls:
        print(f"\n⏳ Processing {url}...")
        lines = fetch_m3u_content(url, args.timeout)
        
        # State tracker to apply cleanup only to URL lines
        expecting_url = False
        
        for line in lines:
            stripped_line = line.strip()
            
            if not stripped_line:
                continue # Skip empty lines

            # 1. Ignore #EXTM3U headers from source files (we already added one)
            if stripped_line.startswith('#EXTM3U'):
                continue
                
            # 2. Process ALL tags that begin with '#EXT' (e.g., #EXTINF, #EXT-X-KEY, #EXT-X-STREAM-INF)
            if stripped_line.startswith('#EXT'):
                combined_lines.append(stripped_line)
                
                # Only set expecting_url flag for the metadata lines that precede a stream URL
                if stripped_line.startswith('#EXTINF'):
                    expecting_url = True
                else:
                    expecting_url = False # Critical: Reset for other EXT tags like #EXT-X-VERSION or #EXT-X-TARGETDURATION

                continue
                
            # 3. Process Stream URLs (This is where the cleanup happens)
            if stripped_line.startswith(('http://', 'https://', 'rtsp://')):
                cleaned_url = clean_stream_url(stripped_line)
                combined_lines.append(cleaned_url)
                
                # Count and reset only if we were expecting a URL (i.e., after #EXTINF)
                if expecting_url:
                    processed_stream_count += 1
                
                # Reset state regardless of whether we counted it or not
                expecting_url = False 
                continue
                
            # 4. Skip all other lines (plain comments, unknown tags, etc.)
            if stripped_line.startswith('#'):
                continue

    # 5. Final Output
    if processed_stream_count > 0:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write('\n'.join(combined_lines) + '\n') # Ensure final newline
        
        print("\n" + "="*50)
        print(f"🎉 Final Playlist Created!")
        print(f"File: {args.output}")
        print(f"Total Clean Streams: {processed_stream_count}")
        print("="*50)
    else:
        print(f"\n⚠️ No valid streams were successfully processed. {args.output} was not created or updated.")

if __name__ == "__main__":
    main()
