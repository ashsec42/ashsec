import argparse
import os
import re
import requests
from typing import List, Dict, Optional, Tuple

# --- Configuration Constants ---
DEFAULT_OUTPUT_FILE = "ashsec.m3u"
DEFAULT_TIMEOUT = 15
DEFAULT_GROUP_TITLE = "ZZ - Unsorted" # Group for streams missing a title
# --------------------------------------------------------

def fetch_m3u_content(url: str, timeout: int) -> List[str]:
    """
    Fetches M3U content from a URL, handling network errors gracefully.
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        print(f"✅ Success: Fetched content from {url}")
        return response.text.splitlines()
    except requests.exceptions.Timeout:
        print(f"❌ Error: Request timed out fetching {url} after {timeout}s.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: Failed to fetch {url}: {e}")
    return []

def extract_group_title(extinf_line: str) -> str:
    """
    Safely extracts the group-title attribute from an #EXTINF line.
    
    Returns:
        The extracted group title string, or a default group name if not found.
    """
    # Regex to find group-title="...content..."
    match = re.search(r'group-title="([^"]*)"', extinf_line)
    
    if match:
        title = match.group(1).strip()
        return title if title else DEFAULT_GROUP_TITLE
    
    return DEFAULT_GROUP_TITLE

def extract_channel_name(extinf_line: str) -> str:
    """
    Extracts the display name (the part after the comma) from the #EXTINF line.
    """
    parts = extinf_line.split(',', 1)
    return parts[1].strip() if len(parts) > 1 else ""

def main():
    """Main function to extract, group, sort, and combine M3U playlist content."""
    parser = argparse.ArgumentParser(description="Combines and sorts multiple M3U playlists by 'group-title' for better user experience.")
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

    # Data structure: { "Group Title": [(#EXTINF line, URL line), ...] }
    grouped_streams: Dict[str, List[Tuple[str, str]]] = {}
    total_streams = 0

    for url in urls:
        print(f"\n⏳ Processing {url}...")
        lines = fetch_m3u_content(url, args.timeout)
        
        if not lines:
            continue
            
        # Iterate over lines, looking for pairs of #EXTINF followed by a URL
        current_extinf: Optional[str] = None
        
        for line in lines:
            stripped_line = line.strip()
            
            # Skip empty lines entirely
            if not stripped_line:
                continue 
            
            # 1. Store Metadata Line
            if stripped_line.startswith('#EXTINF'):
                current_extinf = stripped_line
                
            # 2. Check for Stream URL (only if preceded by metadata)
            # This is the tolerant step: if current_extinf is set, we grab the next URL line,
            # ignoring anything that isn't a stream URL.
            elif current_extinf and stripped_line.startswith(('http://', 'https://', 'rtsp://')):
                # We found a stream URL immediately following an #EXTINF tag.
                
                # Grouping Logic
                group = extract_group_title(current_extinf)
                
                if group not in grouped_streams:
                    grouped_streams[group] = []
                
                # Add the pair to the group list
                grouped_streams[group].append((current_extinf, stripped_line))
                total_streams += 1
                
                # Reset the metadata line for the next stream
                current_extinf = None
            
            # 3. If any other line appears (like an HLS tag, or a non-EXT comment),
            #    we simply ignore it without resetting current_extinf. This allows 
            #    the parser to bridge over empty lines or comments until it finds the stream URL.
            #    If a new #EXTINF is found, it automatically overwrites current_extinf.


    # --- Re-assembly (Writing the Final Playlist) ---
    final_output: List[str] = ["#EXTM3U"]
    
    # Sort groups alphabetically (using the extracted title as the key)
    sorted_groups = sorted(grouped_streams.keys())
    
    for group_title in sorted_groups:
        streams = grouped_streams[group_title]
        
        # FIX: Use a simpler, safer group separator comment line 
        final_output.append(f"\n#-- {group_title} ({len(streams)} Streams) --")
        
        # Sort streams within the group alphabetically by channel name
        streams.sort(key=lambda x: extract_channel_name(x[0]))
        
        for extinf, url_line in streams:
            # Append the original #EXTINF line
            final_output.append(extinf)
            # Append the original, UNTOUCHED stream URL (Preserves Jio Integrity)
            final_output.append(url_line)

    # 4. Final Output File Write
    if total_streams > 0:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write('\n'.join(final_output) + '\n') 
        
        print("\n" + "="*50)
        print(f"🎉 Final Grouped Playlist Created!")
        print(f"File: {args.output}")
        print(f"Total Groups: {len(sorted_groups)}")
        print(f"Total Streams Processed: {total_streams}")
        print("="*50)
    else:
        print(f"\n⚠️ No valid streams were successfully processed. {args.output} was not created or updated.")

if __name__ == "__main__":
    main()
