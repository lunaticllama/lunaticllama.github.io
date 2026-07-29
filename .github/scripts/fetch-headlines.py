import urllib.request
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone

RSS_URL = 'https://news.google.com/rss/search?q=site:wsj.com&hl=en-US&gl=US&ceid=US:en'
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
    xml_bytes = fetch()
    items     = parse(xml_bytes)
    print(f"Fetched {len(items)} headlines")
    payload = {
        'updated': datetime.now(timezone.utc).isoformat(),
        'items':   items,
    }
    with open(OUTPUT, 'w') as f:
        json.dump(payload, f, indent=2)

if __name__ == '__main__':
    main()
