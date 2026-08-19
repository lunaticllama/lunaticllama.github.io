import urllib.request
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone

# ── Headlines ─────────────────────────────────────────────

RSS_URL          = 'https://news.google.com/rss/search?q=site:wsj.com&hl=en-US&gl=US&ceid=US:en'
HEADLINES_OUTPUT = 'data/wsj-headlines.json'
SKIP_TITLES      = ['print edition']

def fetch_rss():
    req = urllib.request.Request(
        RSS_URL,
        headers={'User-Agent': 'Mozilla/5.0 (compatible; dashboard-bot/1.0)'}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def parse_headlines(xml_bytes):
    root = ET.fromstring(xml_bytes)
    headlines = []
    for item in root.findall('.//item'):
        title    = (item.findtext('title') or '').strip()
        link     = (item.findtext('link')  or '').strip()
        pub_date = (item.findtext('pubDate') or '').strip()
        if not title:
            continue
        if any(skip in title.lower() for skip in SKIP_TITLES):
            continue
        headlines.append({'title': title, 'link': link, 'pubDate': pub_date})
        if len(headlines) == 5:
            break
    return headlines

# ── Market data ───────────────────────────────────────────

MARKET_URL    = ('https://query1.finance.yahoo.com/v6/finance/quote'
                 '?symbols=%5EGSPC%2C%5EDJI%2C%5EIXIC')
MARKET_OUTPUT = 'data/market.json'
MARKET_LABELS = ['S&P 500', 'Dow', 'Nasdaq']

def fetch_market():
    req = urllib.request.Request(
        MARKET_URL,
        headers={
            'User-Agent': 'Mozilla/5.0 (compatible; dashboard-bot/1.0)',
            'Accept': 'application/json',
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def parse_market(data):
    quotes = data['quoteResponse']['result']
    items = []
    for i, q in enumerate(quotes):
        items.append({
            'label':     MARKET_LABELS[i],
            'price':     q['regularMarketPrice'],
            'change':    q['regularMarketChange'],
            'changePct': q['regularMarketChangePercent'],
            'state':     q.get('marketState', ''),
        })
    return items

# ── Main ──────────────────────────────────────────────────

def main():
    os.makedirs('data', exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    # Headlines
    xml_bytes = fetch_rss()
    headlines = parse_headlines(xml_bytes)
    print(f"Fetched {len(headlines)} headlines")
    with open(HEADLINES_OUTPUT, 'w') as f:
        json.dump({'updated': now, 'items': headlines}, f, indent=2)

    # Market data
    market_data = fetch_market()
    quotes = parse_market(market_data)
    print(f"Fetched {len(quotes)} market quotes")
    with open(MARKET_OUTPUT, 'w') as f:
        json.dump({'updated': now, 'items': quotes}, f, indent=2)

if __name__ == '__main__':
    main()
