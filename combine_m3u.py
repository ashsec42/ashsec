import os
from pathlib import Path
import sys

def main():
    args = parse_args()

    # If input file exists, read it normally
    input_path = Path(args.input)
    if input_path.exists():
        links = read_links(input_path)
    else:
        # Read M3U links directly from GitHub secret
        secret_links = os.getenv("M3U_LINKS")
        if not secret_links:
            print(f"ERROR: input file '{args.input}' not found and M3U_LINKS secret is missing", file=sys.stderr)
            sys.exit(1)
        links = [l.strip() for l in secret_links.splitlines() if l.strip()]

    session = requests.Session()
    all_entries = []
    for link in links:
        try:
            print(f"Fetching: {link}")
            content = fetch_content(link, timeout=args.timeout, session=session)
            entries = list(parse_m3u(content))
            print(f"  -> {len(entries)} entries parsed")
            all_entries.extend(entries)
        except Exception as e:
            print(f"Warning: failed to fetch/parse {link}: {e}", file=sys.stderr)

    final_entries = list(combine(all_entries, dedupe=not args.no_dedupe))

    with Path(args.output).open('w', encoding='utf-8') as out:
        out.write('#EXTM3U\n')
        for extinf, url in final_entries:
            if extinf:
                out.write(f'{extinf}\n')
            out.write(f'{url}\n')

    print(f"Wrote {len(final_entries)} entries to {args.output} (dedupe={'off' if args.no_dedupe else 'on'})")
