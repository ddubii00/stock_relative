from flask import Flask, jsonify, request, render_template
import json
import requests
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import os

app = Flask(__name__)

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
    '삼디': '삼성SDI',
    '셀트': '셀트리온',
    '네바': 'NAVER',
    '카카': '카카오'
}

def load_stocks_db():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'stocks.json')
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading stocks.json: {e}")
        return []

stocks_db = load_stocks_db()

# --- US STOCKS SUPPORT CONSTANTS & HELPER FUNCTIONS ---
SECTOR_ETF_MAP = {
    'Technology': 'XLK',
    'Electronic Technology': 'XLK',
    'Financial Services': 'XLF',
    'Finance': 'XLF',
    'Healthcare': 'XLV',
    'Health Technology': 'XLV',
    'Consumer Cyclical': 'XLY',
    'Consumer Durables': 'XLY',
    'Industrials': 'XLI',
    'Industrial Services': 'XLI',
    'Consumer Staples': 'XLP',
    'Consumer Defensive': 'XLP',
    'Energy': 'XLE',
    'Utilities': 'XLU',
    'Real Estate': 'XLRE',
    'Basic Materials': 'XLB',
    'Communication Services': 'XLC'
}

US_PEERS_MAP = {
    'Technology': ['AAPL', 'MSFT', 'NVDA', 'AVGO', 'ORCL', 'CRM'],
    'Electronic Technology': ['AAPL', 'MSFT', 'NVDA', 'AVGO', 'ORCL', 'CRM'],
    'Financial Services': ['JPM', 'BAC', 'MS', 'GS', 'WFC', 'V'],
    'Finance': ['JPM', 'BAC', 'MS', 'GS', 'WFC', 'V'],
    'Healthcare': ['LLY', 'UNH', 'JNJ', 'ABBV', 'MRK', 'PFE'],
    'Health Technology': ['LLY', 'UNH', 'JNJ', 'ABBV', 'MRK', 'PFE'],
    'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX'],
    'Consumer Durables': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX'],
    'Industrials': ['GE', 'CAT', 'UNP', 'HON', 'RTX', 'LMT'],
    'Industrial Services': ['GE', 'CAT', 'UNP', 'HON', 'RTX', 'LMT'],
    'Consumer Staples': ['PG', 'KO', 'PEP', 'COST', 'WMT', 'TGT'],
    'Consumer Defensive': ['PG', 'KO', 'PEP', 'COST', 'WMT', 'TGT'],
    'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC'],
    'Utilities': ['NEE', 'SO', 'DUK', 'D', 'AEP', 'SRE'],
    'Real Estate': ['PLD', 'AMT', 'EQIX', 'CCI', 'WY', 'PSA'],
    'Basic Materials': ['LIN', 'APD', 'SHW', 'FCX', 'NEM', 'CTVA'],
    'Communication Services': ['META', 'GOOGL', 'NFLX', 'DIS', 'TMUS', 'VZ']
}

US_TICKER_NAMES = {
    'AAPL': '애플 (Apple)',
    'MSFT': '마이크로소프트 (Microsoft)',
    'NVDA': '엔비디아 (NVIDIA)',
    'AVGO': '브로드컴 (Broadcom)',
    'ORCL': '오라클 (Oracle)',
    'CRM': '세일즈포스 (Salesforce)',
    'JPM': 'JP모건 (JPMorgan)',
    'BAC': '뱅크오브아메리카 (BAC)',
    'MS': '모건스탠리 (Morgan Stanley)',
    'GS': '골드만삭스 (Goldman Sachs)',
    'WFC': '웰스파고 (Wells Fargo)',
    'V': '비자 (Visa)',
    'LLY': '일라이릴리 (Eli Lilly)',
    'UNH': '유나이티드헬스 (UnitedHealth)',
    'JNJ': '존슨앤존슨 (Johnson & Johnson)',
    'ABBV': '애브비 (AbbVie)',
    'MRK': '머크 (Merck)',
    'PFE': '화이자 (Pfizer)',
    'AMZN': '아마존 (Amazon)',
    'TSLA': '테슬라 (Tesla)',
    'HD': '홈디포 (Home Depot)',
    'MCD': '맥도날드 (McDonalds)',
    'NKE': '나이키 (Nike)',
    'SBUX': '스타벅스 (Starbucks)',
    'GE': '제네럴일렉트릭 (GE)',
    'CAT': '캐터필러 (Caterpillar)',
    'UNP': '유니온퍼시픽 (Union Pacific)',
    'HON': '허니웰 (Honeywell)',
    'RTX': '레이시온 (RTX)',
    'LMT': '록히드마틴 (Lockheed Martin)',
    'PG': '프록터앤갬블 (P&G)',
    'KO': '코카콜라 (Coca-Cola)',
    'PEP': '펩시코 (PepsiCo)',
    'COST': '코스트코 (Costco)',
    'WMT': '월마트 (Walmart)',
    'TGT': '타겟 (Target)',
    'XOM': '엑슨모빌 (ExxonMobil)',
    'CVX': '쉐브론 (Chevron)',
    'COP': '코노코필립스 (ConocoPhillips)',
    'SLB': '슐럼버거 (Schlumberger)',
    'EOG': 'EOG리소스 (EOG Resources)',
    'MPC': '마라톤페트롤리엄 (Marathon)',
    'NEE': '넥스트에라 (NextEra)',
    'SO': '서던컴퍼니 (Southern Co)',
    'DUK': '듀크에너지 (Duke Energy)',
    'D': '도미니언 (Dominion)',
    'AEP': '아메리칸일렉트릭 (AEP)',
    'SRE': '셈프라에너지 (Sempra)',
    'PLD': '프로로지스 (Prologis)',
    'AMT': '아메리칸타워 (American Tower)',
    'EQIX': '에퀴닉스 (Equinix)',
    'CCI': '크라운캐슬 (Crown Castle)',
    'WY': '와이어하우저 (Weyerhaeuser)',
    'PSA': '퍼블릭스토리지 (Public Storage)',
    'LIN': '린데 (Linde)',
    'APD': '에어프로덕츠 (Air Products)',
    'SHW': '셔윈윌리엄스 (Sherwin-Williams)',
    'FCX': '프리포트맥모란 (Freeport)',
    'NEM': '뉴몬트 (Newmont)',
    'CTVA': '코르테바 (Corteva)',
    'META': '메타 (Meta)',
    'GOOGL': '구글 (Alphabet)',
    'NFLX': '넷플릭스 (Netflix)',
    'DIS': '디즈니 (Disney)',
    'TMUS': '티모바일 (T-Mobile)',
    'VZ': '버라이즌 (Verizon)',
    'SPY': 'S&P 500 ETF (SPY)'
}

def search_us_stocks(query):
    if not query:
        return []
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=6&newsCount=0"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        res = requests.get(url, headers=headers, timeout=2)
        if res.status_code == 200:
            data = res.json()
            results = []
            for quote in data.get('quotes', []):
                quote_type = quote.get('quoteType')
                exch = quote.get('exchange', '')
                symbol = quote.get('symbol', '')
                if quote_type == 'EQUITY' and exch in ['NYQ', 'NMS', 'NGM', 'PCX', 'ASE'] and '.' not in symbol:
                    results.append({
                        'code': symbol,
                        'name': quote.get('shortname') or quote.get('longname') or symbol,
                        'market': 'NASDAQ' if exch in ['NMS', 'NGM'] else 'NYSE',
                        'sector': quote.get('sector', 'US Stock')
                    })
            return results
    except Exception as e:
        print(f"Error searching US stocks: {e}")
    return []

def fetch_yahoo_history(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            chart = data.get('chart', {}).get('result', [None])[0]
            if chart:
                timestamps = chart.get('timestamp', [])
                indicators = chart.get('indicators', {}).get('quote', [{}])[0]
                opens   = indicators.get('open',   [])
                highs   = indicators.get('high',   [])
                lows    = indicators.get('low',    [])
                closes  = indicators.get('close',  [])
                volumes = indicators.get('volume', [])

                history = []
                for i, ts in enumerate(timestamps):
                    c = closes[i]  if i < len(closes)  and closes[i]  is not None else None
                    o = opens[i]   if i < len(opens)   and opens[i]   is not None else c
                    h = highs[i]   if i < len(highs)   and highs[i]   is not None else c
                    l = lows[i]    if i < len(lows)    and lows[i]    is not None else c
                    v = volumes[i] if i < len(volumes) and volumes[i] is not None else 0
                    if ts is not None and c is not None:
                        date_str = datetime.fromtimestamp(ts).strftime('%Y%m%d')
                        history.append({
                            'date':   date_str,
                            'open':   round(o, 4),
                            'high':   round(h, 4),
                            'low':    round(l, 4),
                            'close':  round(c, 4),
                            'volume': int(v)
                        })
                return history
    except Exception as e:
        print(f"Error fetching Yahoo history for {symbol}: {e}")
    return []

def fetch_us_stock_metadata(symbol):
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}&quotesCount=1"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    name = symbol
    market = 'US'
    sector = 'US Stock'
    try:
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            data = res.json()
            quotes = data.get('quotes', [])
            if quotes:
                quote = quotes[0]
                name = quote.get('shortname') or quote.get('longname') or symbol
                exch = quote.get('exchange', '')
                market = 'NASDAQ' if exch in ['NMS', 'NGM'] else ('NYSE' if exch == 'NYQ' else 'US')
                sector = quote.get('sector', 'US Stock')
    except Exception as e:
        print(f"Error fetching metadata for {symbol}: {e}")
    return name, market, sector

def get_stock_detail(code):
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    res = requests.get(url, headers=headers)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Get sector
    sector_link = soup.find('a', href=re.compile(r'sise_group_detail\.naver\?type=upjong'))
    sector_name = "미분류"
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
    if not sector_code:
        return []
    url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=upjong&no={sector_code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        res = requests.get(url, headers=headers)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        stock_links = soup.find_all('a', href=re.compile(r'/item/main\.naver\?code=(\d+)'))
        seen_codes = set()
        stocks = []
        for link in stock_links:
            href = link.get('href', '')
            match = re.search(r'code=(\d+)', href)
            if match:
                code = match.group(1)
                name = link.text.strip()
                if code not in seen_codes and name:
                    seen_codes.add(code)
                    stocks.append({
                        'code': code,
                        'name': name
                    })
        return stocks
    except Exception as e:
        print(f"Error fetching sector stocks: {e}")
    return []

def parse_date(date_str):
    date_str = date_str.replace('-', '')
    return datetime.strptime(date_str, '%Y%m%d').date()

def calculate_returns(history, periods):
    if not history:
        return {}
        
    dates = [parse_date(x['date']) for x in history]
    closes = [x['close'] for x in history]
    
    if not dates:
        return {}
        
    latest_date = dates[-1]
    latest_close = closes[-1]
    
    returns = {}
    for period_name, days in periods.items():
        if period_name == '1D':
            if len(closes) >= 2:
                returns['1D'] = {
                    'return': ((closes[-1] - closes[-2]) / closes[-2]) * 100,
                    'past_date': dates[-2].strftime('%Y-%m-%d'),
                    'past_close': closes[-2],
                    'latest_close': latest_close
                }
            else:
                returns['1D'] = {
                    'return': 0.0,
                    'past_date': latest_date.strftime('%Y-%m-%d'),
                    'past_close': latest_close,
                    'latest_close': latest_close
                }
            continue
            
        target_date = latest_date - timedelta(days=days)
        closest_idx = 0
        min_diff = abs((dates[0] - target_date).days)
        
        for i, dt in enumerate(dates):
            diff = abs((dt - target_date).days)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
                
        past_close = closes[closest_idx]
        if past_close == 0:
            period_return = 0.0
        else:
            period_return = ((latest_close - past_close) / past_close) * 100
            
        returns[period_name] = {
            'return': period_return,
            'past_date': dates[closest_idx].strftime('%Y-%m-%d'),
            'past_close': past_close,
            'latest_close': latest_close
        }
    return returns

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])
        
    results = []
    
    # 1. Nickname check
    if query in NICKNAMES:
        mapped_name = NICKNAMES[query]
        for s in stocks_db:
            if s['name'].lower() == mapped_name.lower():
                results.append(s)
                break
                
    # 2. Substring matches for KOREAN stocks
    for s in stocks_db:
        if any(r['code'] == s['code'] for r in results):
            continue
        if s['name'].lower().startswith(query) or query in s['name'].lower() or query in s['code']:
            results.append(s)
            if len(results) >= 7:
                break
                
    # 3. Add US Stocks via Yahoo Finance autocomplete
    try:
        us_results = search_us_stocks(query)
        for ur in us_results:
            if len(results) >= 10:
                break
            if not any(r['code'] == ur['code'] for r in results):
                results.append(ur)
    except Exception as e:
        print(f"Error merging US stock search: {e}")
                
    return jsonify(results)

@app.route('/api/performance')
def api_performance():
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({'error': '종목 코드가 제공되지 않았습니다.'}), 400
        
    is_us_stock = not (code.isdigit() and len(code) == 6)
    
    if is_us_stock:
        # --- US STOCK FLOW ---
        try:
            name, market, sector = fetch_us_stock_metadata(code)
            stock = {'code': code, 'name': name, 'market': market, 'sector': sector}
            
            # 1. Fetch US stock history
            stock_history = fetch_yahoo_history(code)
            if not stock_history:
                return jsonify({'error': f'미국 주식 {code}의 주가 이력을 가져오는데 실패했습니다.'}), 404
                
            # 2. Fetch Market index (S&P 500: ^GSPC)
            market_symbol = "S&P 500"
            market_history = fetch_yahoo_history('^GSPC')
            if not market_history:
                return jsonify({'error': 'S&P 500 지수 데이터를 가져오는데 실패했습니다.'}), 404
                
            # 3. Mapped ETF for sector
            etf = SECTOR_ETF_MAP.get(sector, '^GSPC')
            # Fetch Sector ETF history
            sector_history_raw = fetch_yahoo_history(etf)
            if not sector_history_raw:
                sector_history_raw = market_history
                
            # Define peer US symbols
            peer_symbols = US_PEERS_MAP.get(sector, ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'])
            peers_list = [p for p in peer_symbols if p != code][:4]
            
            # Fetch peer histories
            peer_histories = {}
            for p in peers_list:
                try:
                    p_hist = fetch_yahoo_history(p)
                    if len(p_hist) >= 400:
                        peer_histories[p] = p_hist
                except Exception as e:
                    print(f"Error fetching US peer {p}: {e}")
                    
            # Compute sector peer average (normalized to 100 on oldest date)
            aligned_dates = [x['date'] for x in stock_history]
            price_maps = {p_code: {x['date']: x['close'] for x in p_hist} for p_code, p_hist in peer_histories.items()}
            price_maps[code] = {x['date']: x['close'] for x in stock_history}
            
            oldest_date = aligned_dates[0] if aligned_dates else ""
            valid_codes = [c for c in price_maps if oldest_date in price_maps[c]]
            
            sector_history = []
            if oldest_date:
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
            else:
                sector_history = sector_history_raw
                
            # Peers objects for detailed clicks in the frontend
            peers = [{'code': p, 'name': US_TICKER_NAMES.get(p, p)} for p in peers_list]
            sector_name = sector
            sector_code = ""
            
        except Exception as e:
            return jsonify({'error': f'미국 주식 분석 처리 중 에러가 발생했습니다: {str(e)}'}), 500
    else:
        # --- KOREAN STOCK FLOW ---
        # Find stock in local DB
        stock = next((s for s in stocks_db if s['code'] == code), None)
        if not stock:
            # Fallback details fetch
            try:
                url = f"https://finance.naver.com/item/main.naver?code={code}"
                res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                res.encoding = 'utf-8'
                soup = BeautifulSoup(res.text, 'html.parser')
                name_wrap = soup.find('div', class_='wrap_company')
                if not name_wrap:
                    return jsonify({'error': '종목을 찾을 수 없습니다.'}), 404
                name = name_wrap.find('a').text.strip()
                
                market = "코스피"
                description = soup.find('meta', {'name': 'description'})
                if description and '코스닥' in description.get('content', ''):
                    market = '코스닥'
                    
                stock = {'code': code, 'name': name, 'market': market}
            except Exception as e:
                return jsonify({'error': f'종목 정보를 가져오는데 실패했습니다: {str(e)}'}), 404
    
        # 1. Fetch stock and market index histories
        try:
            stock_history = get_price_history(code)
            if not stock_history:
                return jsonify({'error': '주가 이력을 불러올 수 없습니다.'}), 404
                
            market_symbol = "KOSPI" if stock['market'] == "코스피" else "KOSDAQ"
            market_history = get_price_history(market_symbol)
        except Exception as e:
            return jsonify({'error': f'기본 주가 및 지수 이력 로딩 실패: {str(e)}'}), 500
            
        # 2. Get Sector details and peers
        try:
            sector_name, sector_code = get_stock_detail(code)
            sector_stocks = get_sector_stocks(sector_code) if sector_code else []
            
            # Pick top 4 peers excluding this stock
            peers_list = [s for s in sector_stocks if s['code'] != code][:4]
            peers = [{'code': s['code'], 'name': s['name']} for s in peers_list]
        except Exception as e:
            sector_name, sector_code = "미분류", ""
            peers = []
            print(f"Error fetching sector: {e}")
            
        # 3. Fetch peer histories
        peer_histories = {}
        for p in peers:
            try:
                p_hist = get_price_history(p['code'])
                if len(p_hist) >= 400:
                    peer_histories[p['code']] = p_hist
            except Exception as e:
                print(f"Error fetching peer {p['name']} history: {e}")
                
        # 4. Compute sector peer average history (normalized to 100 on oldest date)
        aligned_dates = [x['date'] for x in stock_history]
        price_maps = {p_code: {x['date']: x['close'] for x in p_hist} for p_code, p_hist in peer_histories.items()}
        price_maps[code] = {x['date']: x['close'] for x in stock_history}
        
        oldest_date = aligned_dates[0] if aligned_dates else ""
        valid_codes = [c for c in price_maps if oldest_date in price_maps[c]]
        
        sector_history = []
        if oldest_date:
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
                    
    # 5. Calculate returns for periods
    periods = {
        '1D': 1,
        '1W': 7,
        '1M': 30,
        '3M': 90,
        '6M': 180,
        '12M': 365
    }
    
    # Calculate returns for stock, market and sector average
    stock_returns = calculate_returns(stock_history, periods)
    market_returns = calculate_returns(market_history, periods)
    sector_returns = calculate_returns(sector_history, periods)
    
    # Compile performance comparison table
    performance_table = []
    for p in ['1D', '1W', '1M', '3M', '6M', '12M']:
        s_ret = stock_returns.get(p, {}).get('return', 0.0)
        m_ret = market_returns.get(p, {}).get('return', 0.0)
        sec_ret = sector_returns.get(p, {}).get('return', 0.0)
        
        performance_table.append({
            'period': p,
            'stock_return': s_ret,
            'market_return': m_ret,
            'sector_return': sec_ret,
            'vs_market': s_ret - m_ret,
            'vs_sector': s_ret - sec_ret
        })
        
    # Generate interactive chart series data (last 240 trading days ~ 1 year)
    chart_len = min(250, len(stock_history))
    chart_dates = aligned_dates[-chart_len:]
    chart_start_date = chart_dates[0]
    
    chart_stock = []
    chart_market = []
    chart_sector = []
    
    # Maps for easy lookups
    stock_map = {x['date']: x['close'] for x in stock_history}
    market_map = {x['date']: x['close'] for x in market_history}
    sector_map = {x['date']: x['close'] for x in sector_history}
    
    stock_base = stock_map.get(chart_start_date, 1.0)
    market_base = market_map.get(chart_start_date, 1.0)
    sector_base = sector_map.get(chart_start_date, 1.0)
    
    for date in chart_dates:
        s_val = (stock_map.get(date, stock_base) / stock_base) * 100 if stock_base else 100.0
        m_val = (market_map.get(date, market_base) / market_base) * 100 if market_base else 100.0
        sec_val = (sector_map.get(date, sector_base) / sector_base) * 100 if sector_base else 100.0
        
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        
        chart_stock.append({'date': formatted_date, 'value': s_val})
        chart_market.append({'date': formatted_date, 'value': m_val})
        chart_sector.append({'date': formatted_date, 'value': sec_val})
        
    return jsonify({
        'stock': {
            'code': stock['code'],
            'name': stock['name'],
            'market': stock['market'],
            'sector_name': sector_name,
            'sector_code': sector_code
        },
        'benchmark': market_symbol,
        'peers': peers,
        'table': performance_table,
        'chart': {
            'dates': [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in chart_dates],
            'stock': [x['value'] for x in chart_stock],
            'market': [x['value'] for x in chart_market],
            'sector': [x['value'] for x in chart_sector]
        },
        'ohlc': stock_history
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
