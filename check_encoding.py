import requests
from bs4 import BeautifulSoup
import re

def check_encoding():
    url = "https://finance.naver.com/item/main.naver?code=005930"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    res = requests.get(url, headers=headers)
    
    print("Detected encoding by requests:", res.encoding)
    print("Apparent encoding by requests:", res.apparent_encoding)
    print("Content-Type header:", res.headers.get('Content-Type'))
    
    # Try different decodings
    encodings = ['euc-kr', 'cp949', 'utf-8', 'utf-16']
    for enc in encodings:
        try:
            text = res.content.decode(enc)
            soup = BeautifulSoup(text, 'html.parser')
            name_wrap = soup.find('div', class_='wrap_company')
            name = ""
            if name_wrap and name_wrap.find('a'):
                name = name_wrap.find('a').text.strip()
                
            sector_link = soup.find('a', href=re.compile(r'sise_group_detail\.naver\?type=upjong'))
            sector_name = ""
            if sector_link:
                sector_name = sector_link.text.strip()
                
            print(f"\n--- Decoding with: {enc} ---")
            print("Stock Name:", name)
            print("Sector Name:", sector_name)
        except Exception as e:
            print(f"\nFailed to decode with {enc}: {e}")

if __name__ == '__main__':
    check_encoding()
