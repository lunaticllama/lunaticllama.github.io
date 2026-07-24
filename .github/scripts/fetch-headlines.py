import urllib.request
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone

RSS_URL = 'https://feeds.wsj.com/wsj/xml/rss/3_7085.xml'
OUTPUT  = 'data/wsj-headlines.json'

def fetch():
    req = urllib.request.Request(
        RSS_URL,
        headers={'User-Agent': 'Mozilla/5.0 (compatible; headlines-bot/1.0)'}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = root.findall('.//item')[:5]
    headlines = []
    for item in items:
        title    = (item.findtext('title') or '').strip()
        link     = (item.findtext('link')  or '').strip()
        pub_date = (item.findtext('pubDate') or '').strip()
        if title:
            headlines.append({'title': title, 'link': link, 'pubDate': pub_date})
    return headlines

def main():
    os.makedirs('data', exist_ok=True)
    try:
        xml_bytes = fetch()
        items     = parse(xml_bytes)
        payload   = {
            'updated': datetime.now(timezone.utc).isoformat(),
            'items':   items,
        }
        print(f"Fetched {len(items)} headlines")
    except Exception as e:
        print(f"Error fetching headlines: {e}")
        # Preserve existing file on failure rather than wiping it
        if os.path.exists(OUTPUT):
            print("Keeping existing headlines file.")
            return
        payload = {'updated': None, 'items': []}

    with open(OUTPUT, 'w') as f:
        json.dump(payload, f, indent=2)

if __name__ == '__main__':
    main()
