import requests
from bs4 import BeautifulSoup
import re

def check_sector_encoding():
    url = "https://finance.naver.com/sise/sise_group_detail.naver?type=upjong&no=278"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    res = requests.get(url, headers=headers)
    print("Detected encoding:", res.encoding)
    print("Apparent encoding:", res.apparent_encoding)
    print("Content-Type header:", res.headers.get('Content-Type'))
    
    for enc in ['utf-8', 'euc-kr', 'cp949']:
        try:
            text = res.content.decode(enc)
            soup = BeautifulSoup(text, 'html.parser')
            stock_links = soup.find_all('a', href=re.compile(r'/item/main\.naver\?code=(\d+)'))
            stocks = []
            for link in stock_links[:5]:
                name = link.text.strip()
                if name:
                    stocks.append(name)
            print(f"\n--- Decoded with: {enc} ---")
            print("Sample Stocks:", stocks)
        except Exception as e:
            print(f"\nFailed with {enc}: {e}")

if __name__ == '__main__':
    check_sector_encoding()
