import requests
from bs4 import BeautifulSoup
import re
import json
import time

def parse_market_sum_page(sosok, page):
    url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Find all stock links
    links = soup.find_all('a', href=re.compile(r'/item/main\.(nhn|naver)\?code=(\d+)'))
    
    page_stocks = []
    seen = set()
    for link in links:
        code = re.search(r'code=(\d+)', link.get('href')).group(1)
        name = link.text.strip()
        if code not in seen and name:
            seen.add(code)
            page_stocks.append({
                'code': code,
                'name': name,
                'market': '코스피' if sosok == 0 else '코스닥'
            })
    return page_stocks

def build_db():
    print("Starting stock DB build...")
    all_stocks = []
    
    # 1. KOSPI (sosok=0)
    print("Scraping KOSPI...")
    for page in range(1, 10): # Let's scrape the first 10 pages for KOSPI (500 major stocks)
        try:
            stocks = parse_market_sum_page(0, page)
            if not stocks:
                break
            all_stocks.extend(stocks)
            print(f"  KOSPI Page {page} scraped: Found {len(stocks)} stocks.")
            time.sleep(0.1)
        except Exception as e:
            print(f"  Error on KOSPI page {page}: {e}")
            break
            
    # 2. KOSDAQ (sosok=1)
    print("Scraping KOSDAQ...")
    for page in range(1, 10): # Let's scrape the first 10 pages for KOSDAQ (500 major stocks)
        try:
            stocks = parse_market_sum_page(1, page)
            if not stocks:
                break
            all_stocks.extend(stocks)
            print(f"  KOSDAQ Page {page} scraped: Found {len(stocks)} stocks.")
            time.sleep(0.1)
        except Exception as e:
            print(f"  Error on KOSDAQ page {page}: {e}")
            break
            
    print(f"Scraped {len(all_stocks)} stocks in total.")
    
    # Save to json
    with open('stocks.json', 'w', encoding='utf-8') as f:
        json.dump(all_stocks, f, ensure_ascii=False, indent=2)
    print("Saved to stocks.json successfully!")

if __name__ == '__main__':
    build_db()
