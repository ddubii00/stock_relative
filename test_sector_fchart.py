import requests

def test_sector_chart(code):
    print(f"Testing sector chart fetch for code: {code}")
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=10&requestType=0"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    res = requests.get(url, headers=headers)
    print(f"Status Code: {res.status_code}")
    print(f"Content (first 500 chars):\n{res.text[:500]}")
    print("-" * 50)

if __name__ == '__main__':
    test_sector_chart("278")
    test_sector_chart("005930")
