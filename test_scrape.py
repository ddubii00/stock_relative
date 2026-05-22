import requests
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET

def test_fetch_stock_info(code):
    print(f"Fetching info for code: {code}")
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    res = requests.get(url, headers=headers)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # 1. Get stock name
    name_wrap = soup.find('div', class_='wrap_company')
    if not name_wrap:
        print("Stock name wrap not found.")
        return
    name = name_wrap.find('a').text.strip()
    
    # 2. Get market type (KOSPI or KOSDAQ)
    # The description or class in the html usually indicates this.
    # In Naver Finance, the stock code search or the class shows KOSPI/KOSDAQ.
    # E.g. <img src="..." class="kospi" alt="코스피">
    market_img = name_wrap.find('img', class_=re.compile('(kospi|kosdaq)'))
    market = ""
    if market_img:
        market = market_img.get('alt', '')
    else:
        # fallback search
        description = soup.find('meta', {'name': 'description'})
        if description:
            desc_text = description.get('content', '')
            if '코스피' in desc_text:
                market = '코스피'
            elif '코스닥' in desc_text:
                market = '코스닥'
    
    # 3. Get sector (업종) info
    # The sector name is usually inside a table or link.
    # Let's search for "업종" or look for a link with "sise_group_detail.naver?type=upjong"
    sector_link = soup.find('a', href=re.compile(r'sise_group_detail\.naver\?type=upjong'))
    sector_name = ""
    sector_code = ""
    if sector_link:
        sector_name = sector_link.text.strip()
        href = sector_link.get('href', '')
        match = re.search(r'no=(\d+)', href)
        if match:
            sector_code = match.group(1)
            
    print(f"Name: {name}")
    print(f"Market: {market}")
    print(f"Sector Name: {sector_name}")
    print(f"Sector Code: {sector_code}")

def test_fetch_price_history(code):
    print(f"\nFetching price history for code: {code}")
    # Naver fchart API
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=500&requestType=0"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    res = requests.get(url, headers=headers)
    root = ET.fromstring(res.text)
    items = root.findall('.//item')
    print(f"Total data points retrieved: {len(items)}")
    if items:
        # Print first and last item
        print("First data point (oldest):", items[0].attrib['data'])
        print("Last data point (newest):", items[-1].attrib['data'])

if __name__ == '__main__':
    test_fetch_stock_info("005930")  # Samsung Electronics
    test_fetch_price_history("005930")
    
    # Let's also fetch KOSPI index history
    test_fetch_price_history("KOSPI")
    test_fetch_price_history("KOSDAQ")
