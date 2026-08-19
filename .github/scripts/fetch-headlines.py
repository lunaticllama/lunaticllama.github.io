import urllib.request
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone

# -- Headlines -------------------------------------------------

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

# -- Market data (Yahoo Finance v8 chart, one request per symbol) --

MARKET_OUTPUT  = 'data/market.json'
MARKET_SYMBOLS = [
    ('%5EGSPC', 'S&P 500'),
    ('%5EDJI',  'Dow'),
    ('%5EIXIC', 'Nasdaq'),
]

def fetch_one_quote(encoded_symbol):
    url = ('https://query1.finance.yahoo.com/v8/finance/chart/'
           + encoded_symbol + '?interval=1d&range=1d')
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (compatible; dashboard-bot/1.0)',
            'Accept': 'application/json',
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def fetch_market():
    items = []
    for symbol, label in MARKET_SYMBOLS:
        data = fetch_one_quote(symbol)
        meta  = data['chart']['result'][0]['meta']
        price = meta['regularMarketPrice']
        prev  = meta.get('chartPreviousClose') or meta.get('previousClose') or price
        change = price - prev
        pct    = (change / prev * 100) if prev else 0
        items.append({
            'label':     label,
            'price':     price,
            'change':    change,
            'changePct': pct,
            'state':     meta.get('marketState', ''),
        })
    return items

# -- Main ------------------------------------------------------

def main():
    os.makedirs('data', exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    # Headlines (fail loudly — this is the primary purpose)
    xml_bytes = fetch_rss()
    headlines = parse_headlines(xml_bytes)
    print(f"Fetched {len(headlines)} headlines")
    with open(HEADLINES_OUTPUT, 'w') as f:
        json.dump({'updated': now, 'items': headlines}, f, indent=2)

    # Market data (fail softly — keep old file if fetch fails)
    try:
        quotes = fetch_market()
        print(f"Fetched {len(quotes)} market quotes")
        with open(MARKET_OUTPUT, 'w') as f:
            json.dump({'updated': now, 'items': quotes}, f, indent=2)
    except Exception as e:
        print(f"WARNING: market fetch failed ({e}), keeping existing data")

if __name__ == '__main__':
    main()
