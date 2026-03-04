# debug_minkabu2.py
import requests
from bs4 import BeautifulSoup
import re

urls = [
    "https://minkabu.jp/stock/NKVI",
    "https://finance.yahoo.co.jp/quote/NKVI",
    "https://jp.investing.com/indices/nikkei-volatility",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

for url in urls:
    try:
        res = requests.get(url, headers=headers, timeout=10)
        print(f"\n{url}")
        print(f"ステータス: {res.status_code}")
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for tag in soup.find_all(string=re.compile(r'\d{2,3}\.\d{2}')):
                text = tag.strip()
                if text and len(text) < 20:
                    print(f"  値: '{text}' | 親: <{tag.parent.name} class='{tag.parent.get('class')}'>")
    except Exception as e:
        print(f"  エラー: {e}")