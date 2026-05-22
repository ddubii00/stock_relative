import requests
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

def get_stock_code_and_market(query):
    # Naver stock autocomplete API
    # https://ac.finance.naver.com/ac?q={query}&q_enc=utf-8&st=111&r_lt=111&r_format=json&r_enc=utf-8&r_unicode=0&t_koreng=1
    url = f"https://ac.finance.naver.com/ac?q={query}&q_enc=utf-8&st=111&r_lt=111&r_format=json&r_enc=utf-8&r_unicode=0&t_koreng=1"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        # The structure is: items is a list of lists: [[["name", "code", "other", ...]]]
        items = data.get('items', [])
        if items and items[0]:
            match_list = items[0]
            # Print matching results
            print("Autocomplete results:")
            for m in match_list:
                print(f"  Name: {m[0]}, Code: {m[1]}")
            # Get the best match
            best_match = match_list[0]
            return best_match[1], best_match[0] # code, name
    except Exception as e:
        print(f"Error in autocomplete search: {e}")
    
    # Fallback: exact match in a small manual list or scrape search
    return None, None

def get_stock_detail(code):
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Get stock name
    name_wrap = soup.find('div', class_='wrap_company')
    if not name_wrap:
        return None
    name = name_wrap.find('a').text.strip()
    
    # Get market
    market = ""
    market_img = name_wrap.find('img', class_=re.compile('(kospi|kosdaq)'))
    if market_img:
        market = market_img.get('alt', '')
    else:
        description = soup.find('meta', {'name': 'description'})
        if description:
            desc_text = description.get('content', '')
            if '코스피' in desc_text:
                market = '코스피'
            elif '코스닥' in desc_text:
                market = '코스닥'
                
    # Get sector
    sector_link = soup.find('a', href=re.compile(r'sise_group_detail\.naver\?type=upjong'))
    sector_name = ""
    sector_code = ""
    if sector_link:
        sector_name = sector_link.text.strip()
        href = sector_link.get('href', '')
        match = re.search(r'no=(\d+)', href)
        if match:
            sector_code = match.group(1)
            
    return {
        'code': code,
        'name': name,
        'market': market,
        'sector_name': sector_name,
        'sector_code': sector_code
    }

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
    
    # Sort history by date ascending
    history = sorted(history, key=lambda x: x['date'])
    latest = history[-1]
    latest_date = datetime.strptime(latest['date'], '%Y%m%d')
    latest_close = latest['close']
    
    dates = [x['date'] for x in history]
    closes = [x['close'] for x in history]
    
    returns = {}
    
    # Find matching index for each period
    for period_name, days_delta in target_periods.items():
        target_date = latest_date - timedelta(days=days_delta)
        # Find closest date
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

def run_test():
    # 1. Search for "삼전"
    query = "삼전"
    print(f"Searching for query: '{query}'")
    code, name = get_stock_code_and_market(query)
    if not code:
        print("Stock not found!")
        return
        
    print(f"Resolved to stock: {name} ({code})")
    
    # 2. Get details (market, sector)
    details = get_stock_detail(code)
    print("Details:", details)
    
    # 3. Fetch history for stock and index
    stock_history = get_price_history(code)
    market_symbol = "KOSPI" if details['market'] == "코스피" else "KOSDAQ"
    market_history = get_price_history(market_symbol)
    
    # 4. Fetch sector history
    # Get all stocks in sector
    sector_stocks = get_sector_stocks(details['sector_code'])
    print(f"Sector '{details['sector_name']}' has {len(sector_stocks)} stocks.")
    
    # We will pick 4 stocks in the sector that are not our main stock
    peer_stocks = [s for s in sector_stocks if s['code'] != code][:4]
    print(f"Selected peer stocks for sector average: {[s['name'] for s in peer_stocks]}")
    
    # Fetch histories
    peer_histories = {}
    for p in peer_stocks:
        p_hist = get_price_history(p['code'])
        # Only use if we have sufficient data
        if len(p_hist) >= 400:
            peer_histories[p['code']] = p_hist
            
    # Compute sector index: average return of peer stocks + main stock
    # For each date in main stock's history, find the close for each peer
    # Let's align by dates
    aligned_dates = [x['date'] for x in stock_history]
    sector_history = []
    
    # We will compute the return relative to the starting date
    # Start date index: 0
    # For each stock, its index starts at 100.
    # Sector index at t = average(stock_i_t / stock_i_0 * 100)
    # Then sector return from past to latest can be computed from this sector index!
    
    # Let's find common start dates or just do simple average of daily return index
    # To keep it robust, let's create a map of date -> price for each stock
    price_maps = {}
    for p_code, p_hist in peer_histories.items():
        price_maps[p_code] = {x['date']: x['close'] for x in p_hist}
    price_maps[code] = {x['date']: x['close'] for x in stock_history}
    
    # Filter peer codes that actually had data on the oldest date
    oldest_date = aligned_dates[0]
    valid_codes = [c for c in price_maps if oldest_date in price_maps[c]]
    
    print(f"Computing sector index with {len(valid_codes)} stocks: {[name if c == code else next(s['name'] for s in peer_stocks if s['code'] == c) for c in valid_codes]}")
    
    for date in aligned_dates:
        # Sum of normalized prices
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
                'close': norm_sum / count # Sector Index Value (starts at 100)
            })
            
    # Target periods in calendar days
    periods = {
        '1W': 7,
        '1M': 30,
        '3M': 91,
        '6M': 182,
        '12M': 365
    }
    
    # Calculate returns
    stock_returns = calculate_returns(stock_history, periods)
    market_returns = calculate_returns(market_history, periods)
    sector_returns = calculate_returns(sector_history, periods)
    
    # Display relative returns
    print("\n--- Relative Returns Comparison Table ---")
    print(f"{'Period':<8} | {name + ' (%)':<12} | {market_symbol + ' (%)':<12} | {'Sector (%)':<12} | {'vs Market (pp)':<14} | {'vs Sector (pp)':<14}")
    print("-" * 85)
    for p in periods:
        s_ret = stock_returns.get(p, {}).get('return', 0.0)
        m_ret = market_returns.get(p, {}).get('return', 0.0)
        sec_ret = sector_returns.get(p, {}).get('return', 0.0)
        
        vs_market = s_ret - m_ret
        vs_sector = s_ret - sec_ret
        
        print(f"{p:<8} | {s_ret:<12.2f} | {m_ret:<12.2f} | {sec_ret:<12.2f} | {vs_market:<+14.2f} | {vs_sector:<+14.2f}")

if __name__ == '__main__':
    run_test()
