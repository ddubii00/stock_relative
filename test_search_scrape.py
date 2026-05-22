import requests
from bs4 import BeautifulSoup
import urllib.parse

def test_search_stock(query):
    print(f"Scraping search for query: '{query}'")
    encoded_query = urllib.parse.quote(query, encoding='euc-kr')
    url = f"https://finance.naver.com/search/searchList.naver?query={encoded_query}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr'
    
    with open("search_out.html", "w", encoding="utf-8") as f:
        f.write(res.text)
        
    print(f"Saved HTML. Status: {res.status_code}. Content length: {len(res.text)}")

if __name__ == '__main__':
    test_search_stock("삼성전자")
