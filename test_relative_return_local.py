import json
import requests
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Common Korean stock nicknames
NICKNAMES = {
    '삼전': '삼성전자',
    '삼전우': '삼성전자우',
    '하닉': 'SK하이닉스',
    '슼하': 'SK하이닉스',
    '현차': '현대자동차',
    '현대차': '현대자동차',
    '기아차': '기아',
    '엘전': 'LG전자',
    '엘디': 'LG디스플레이',
    '엘화': 'LG화학',
    '엔솔': 'LG에너지솔루션',
    '삼바': '삼성바이오로직스',
    '삼에스': '삼성SDI',
    '삼물': '삼성물산',
    '네이버': 'NAVER',
    '카카오': '카카오',
    '셀케': '셀트리온헬스케어',
    '포뷰': '포스코퓨처엠',
    '포홀': 'POSCO홀딩스',
    '포스코홀': 'POSCO홀딩스',
    '에코': '에코프로',
    '에비': '에코프로비엠',
}

def load_stocks_db():
    with open('stocks.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def search_stock_local(query, db):
    # Standardize query
    q = query.strip().lower()
    
    # 1. Nickname check
    if q in NICKNAMES:
        mapped_name = NICKNAMES[q]
        print(f"Mapped nickname '{q}' -> '{mapped_name}'")
        for s in db:
            if s['name'].lower() == mapped_name.lower():
                return s
                
    # 2. Exact match
    for s in db:
        if s['name'].lower() == q:
            return s
            
    # 3. Substring match (starts with)
    for s in db:
        if s['name'].lower().startswith(q):
            return s
            
    # 4. Substring match (contains)
    for s in db:
        if q in s['name'].lower():
            return s
            
    return None

def get_stock_detail(code):
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Get sector (업종)
    sector_link = soup.find('a', href=re.compile(r'sise_group_detail\.naver\?type=upjong'))
    sector_name = ""
    sector_code = ""
    if sector_link:
        sector_name = sector_link.text.strip()
        href = sector_link.get('href', '')
        match = re.search(r'no=(\d+)', href)
        if match:
            sector_code = match.group(1)
            
    return sector_name, sector_code

def get_price_history(code, count=500):
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count={count}&requestType=0"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    res = requests.get(url, headers=headers)
    root = ET.fromstring(res.text)
    items = root.findall('.//item')
    
    history = []
    for item in items:
        data_str = item.attrib['data']
        # format: Date|Open|High|Low|Close|Volume
        parts = data_str.split('|')
        if len(parts) >= 5:
            history.append({
                'date': parts[0],
                'open': float(parts[1]),
                'high': float(parts[2]),
                'low': float(parts[3]),
                'close': float(parts[4]),
                'volume': float(parts[5]) if len(parts) > 5 else 0.0
            })
    return history

def get_sector_stocks(sector_code):
    url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=upjong&no={sector_code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    stock_links = soup.find_all('a', href=re.compile(r'/item/main\.naver\?code=(\d+)'))
    seen_codes = set()
    stocks = []
    for link in stock_links:
        code = re.search(r'code=(\d+)', link.get('href', '')).group(1)
        name = link.text.strip()
        if code not in seen_codes and name:
            seen_codes.add(code)
            stocks.append({'code': code, 'name': name})
    return stocks

def calculate_returns(history, target_periods):
    if not history:
        return {}
    
    history = sorted(history, key=lambda x: x['date'])
    latest = history[-1]
    latest_date = datetime.strptime(latest['date'], '%Y%m%d')
    latest_close = latest['close']
    
    dates = [x['date'] for x in history]
    closes = [x['close'] for x in history]
    
    returns = {}
    
    for period_name, days_delta in target_periods.items():
        target_date = latest_date - timedelta(days=days_delta)
        closest_idx = None
        min_diff = timedelta(days=999999)
        for idx, d_str in enumerate(dates):
            d_dt = datetime.strptime(d_str, '%Y%m%d')
            diff = abs(d_dt - target_date)
            if diff < min_diff:
                min_diff = diff
                closest_idx = idx
        
        if closest_idx is not None:
            past_close = closes[closest_idx]
            period_return = (latest_close - past_close) / past_close * 100
            returns[period_name] = {
                'return': period_return,
                'past_date': dates[closest_idx],
                'past_close': past_close,
                'latest_close': latest_close
            }
    return returns

def main():
    db = load_stocks_db()
    
    # 1. Search stock
    query = "삼전"
    stock = search_stock_local(query, db)
    if not stock:
        print(f"Stock not found for query: '{query}'")
        return
        
    print(f"Found stock in database: {stock['name']} ({stock['code']}) - Market: {stock['market']}")
    
    # 2. Get Sector details
    sector_name, sector_code = get_stock_detail(stock['code'])
    print(f"Sector Name: {sector_name}, Sector Code: {sector_code}")
    
    # 3. Fetch Price histories
    stock_history = get_price_history(stock['code'])
    market_symbol = "KOSPI" if stock['market'] == "코스피" else "KOSDAQ"
    market_history = get_price_history(market_symbol)
    
    # 4. Fetch sector peer stocks and histories
    sector_stocks = get_sector_stocks(sector_code)
    # Pick top 4 peers
    peers = [s for s in sector_stocks if s['code'] != stock['code']][:4]
    print(f"Selected Sector Peers: {[s['name'] for s in peers]}")
    
    peer_histories = {}
    for p in peers:
        p_hist = get_price_history(p['code'])
        if len(p_hist) >= 400:
            peer_histories[p['code']] = p_hist
            
    # 5. Compute sector index series
    aligned_dates = [x['date'] for x in stock_history]
    price_maps = {p_code: {x['date']: x['close'] for x in p_hist} for p_code, p_hist in peer_histories.items()}
    price_maps[stock['code']] = {x['date']: x['close'] for x in stock_history}
    
    oldest_date = aligned_dates[0]
    valid_codes = [c for c in price_maps if oldest_date in price_maps[c]]
    
    sector_history = []
    for date in aligned_dates:
        norm_sum = 0
        count = 0
        for c in valid_codes:
            if date in price_maps[c]:
                base_price = price_maps[c][oldest_date]
                current_price = price_maps[c][date]
                norm_sum += (current_price / base_price) * 100
                count += 1
        if count > 0:
            sector_history.append({
                'date': date,
                'close': norm_sum / count
            })
            
    # Calculate returns
    periods = {
        '1W': 7,
        '1M': 30,
        '3M': 91,
        '6M': 182,
        '12M': 365
    }
    
    stock_returns = calculate_returns(stock_history, periods)
    market_returns = calculate_returns(market_history, periods)
    sector_returns = calculate_returns(sector_history, periods)
    
    print("\n" + "="*80)
    print(f"Relative Performance Table: {stock['name']} ({stock['code']})")
    print(f"Benchmark: {market_symbol} | Sector: {sector_name}")
    print("="*80)
    print(f"{'Period':<6} | {'Stock (%)':<10} | {market_symbol + ' (%)':<11} | {'Sector (%)':<10} | {'vs Market (pp)':<14} | {'vs Sector (pp)':<14}")
    print("-"*80)
    for p in ['1W', '1M', '3M', '6M', '12M']:
        s_ret = stock_returns.get(p, {}).get('return', 0.0)
        m_ret = market_returns.get(p, {}).get('return', 0.0)
        sec_ret = sector_returns.get(p, {}).get('return', 0.0)
        
        vs_market = s_ret - m_ret
        vs_sector = s_ret - sec_ret
        
        print(f"{p:<6} | {s_ret:<10.2f} | {m_ret:<11.2f} | {sec_ret:<10.2f} | {vs_market:<+14.2f} | {vs_sector:<+14.2f}")
    print("="*80)

if __name__ == '__main__':
    main()
