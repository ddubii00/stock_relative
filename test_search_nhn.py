import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

def test_search_stock(query):
    print(f"Scraping search for query: '{query}'")
    encoded_query = urllib.parse.quote(query, encoding='euc-kr')
    url = f"https://finance.naver.com/search/searchList.nhn?query={encoded_query}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr'
    
    print(f"Status Code: {res.status_code}")
    print(f"Content Length: {len(res.text)}")
    
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Check for direct item page wrap_company
    name_wrap = soup.find('div', class_='wrap_company')
    if name_wrap:
        name = name_wrap.find('a').text.strip()
        print(f"Direct match found stock: {name}")
        href_el = soup.find('a', href=re.compile(r'/item/main\.(nhn|naver)\?code=(\d+)'))
        if href_el:
            code = re.search(r'code=(\d+)', href_el.get('href')).group(1)
            print(f"Code: {code}")
            return code, name
            
    # Check for search list table with class "type_2"
    table = soup.find('table', class_='type_2')
    if table:
        rows = table.find_all('tr')
        print(f"Found table. Rows count: {len(rows)}")
        for row in rows:
            link = row.find('a', href=re.compile(r'/item/main\.(nhn|naver)\?code=(\d+)'))
            if link:
                code = re.search(r'code=(\d+)', link.get('href')).group(1)
                name = link.text.strip()
                print(f"List Match: {name} ({code})")
                return code, name
                
    # Fallback to any code link
    links = soup.find_all('a', href=re.compile(r'code=(\d+)'))
    print(f"Total links with 'code=': {len(links)}")
    for link in links:
        href = link.get('href', '')
        code = re.search(r'code=(\d+)', href).group(1)
        name = link.text.strip()
        if name and len(code) == 6:
            print(f"Fallback Link Match: {name} ({code})")
            return code, name

    return None, None

if __name__ == '__main__':
    test_search_stock("삼전")
    print("=" * 40)
    test_search_stock("삼성전자")
