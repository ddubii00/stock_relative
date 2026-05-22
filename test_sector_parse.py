import requests
from bs4 import BeautifulSoup
import re

def test_parse_sector(sector_code):
    url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=upjong&no={sector_code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # In Naver Finance, the stock table in sector detail is usually class "type_5" or similar.
    # Let's find links to "/item/main.naver?code="
    stock_links = soup.find_all('a', href=re.compile(r'/item/main\.naver\?code=(\d+)'))
    
    seen_codes = set()
    stocks = []
    for link in stock_links:
        code = re.search(r'code=(\d+)', link.get('href', '')).group(1)
        name = link.text.strip()
        if code not in seen_codes and name:
            seen_codes.add(code)
            stocks.append({'code': code, 'name': name})
            
    print(f"Sector Code {sector_code}: Found {len(stocks)} stocks.")
    print("Top 10 stocks in sector:")
    for idx, s in enumerate(stocks[:10]):
        print(f"{idx+1}. {s['name']} ({s['code']})")

if __name__ == '__main__':
    test_parse_sector("278")  # Semiconductors
