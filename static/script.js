/* ==========================================================================
   Antigravity Stock Relative Returns Dashboard - Frontend Controller
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const searchInput = document.getElementById('stock-search');
    const autocompleteList = document.getElementById('autocomplete-list');
    const clearSearchBtn = document.getElementById('clear-search-btn');
    const spinner = document.getElementById('loading-spinner');
    const recentSearchesContainer = document.getElementById('recent-searches-container');
    const recentSearchesList = document.getElementById('recent-searches-list');
    
    // Views
    const welcomeView = document.getElementById('welcome-view');
    const mainDashboard = document.getElementById('main-dashboard');
    
    // Stock Header Elements
    const stockNameEl = document.getElementById('stock-name');
    const stockCodeBadge = document.getElementById('stock-code-badge');
    const marketBadge = document.getElementById('market-badge');
    const sectorBadge = document.getElementById('sector-badge');
    
    // Table Elements
    const performanceTbody = document.getElementById('performance-tbody');
    
    // Peers Elements
    const peersListContainer = document.getElementById('peers-list');
    
    // Chart Elements
    const periodButtons = document.querySelectorAll('.period-btn');
    let relativeChart = null; // Chart.js instance holder
    
    // State Variables
    let rawChartData = null; // Stores { dates:[], stock:[], market:[], sector:[] }
    let benchmarkSymbol = '지수';
    let rawOhlcData = [];    // Raw OHLC data for daily candlestick
    let candleChartInstance = null; // ApexCharts instance holder
    let volumeChartInstance = null; // ApexCharts volume instance holder
    let macdChartInstance = null;   // ApexCharts MACD instance holder
    
    // Recent Searches Storage Engine
    function saveToRecentSearches(code, name) {
        if (!code || !name) return;
        let recent = JSON.parse(localStorage.getItem('recent_searches') || '[]');
        // Remove duplicate to bring it to the front
        recent = recent.filter(item => item.code !== code);
        // Add to front
        recent.unshift({ code, name });
        // Keep only top 10 recent searches
        recent = recent.slice(0, 10);
        localStorage.setItem('recent_searches', JSON.stringify(recent));
        renderRecentSearches();
    }

    function renderRecentSearches() {
        const recent = JSON.parse(localStorage.getItem('recent_searches') || '[]');
        if (recent.length === 0) {
            recentSearchesContainer.classList.add('hidden');
            return;
        }

        recentSearchesList.innerHTML = '';
        recent.forEach(item => {
            const btn = document.createElement('button');
            btn.className = 'recent-badge';
            btn.textContent = item.name;
            btn.addEventListener('click', () => {
                searchInput.value = item.name;
                loadStockPerformance(item.code);
            });
            recentSearchesList.appendChild(btn);
        });
        recentSearchesContainer.classList.remove('hidden');
    }

    // Initialize Recent Searches
    renderRecentSearches();

    // Popular Queries Clicks
    const popularBtns = document.querySelectorAll('.popular-btn');
    popularBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            searchInput.value = btn.textContent;
            triggerSearch(btn.textContent);
        });
    });

    // 1. Clear Search Bar Event
    clearSearchBtn.addEventListener('click', () => {
        searchInput.value = '';
        searchInput.focus();
        clearSearchBtn.style.display = 'none';
        autocompleteList.classList.add('hidden');
    });

    // 2. Search Input Keyup Event (Debounced Autocomplete)
    let debounceTimer;
    searchInput.addEventListener('keyup', (e) => {
        const query = searchInput.value.trim();
        
        // Toggle Clear button visibility
        if (query.length > 0) {
            clearSearchBtn.style.display = 'block';
        } else {
            clearSearchBtn.style.display = 'none';
            autocompleteList.classList.add('hidden');
            return;
        }

        // Detect Enter Key
        if (e.key === 'Enter') {
            triggerSearch(query);
            return;
        }

        // Live autocomplete search after 200ms debounce
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchAutocomplete(query);
        }, 200);
    });

    // Close autocomplete when clicking outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !autocompleteList.contains(e.target)) {
            autocompleteList.classList.add('hidden');
        }
    });

    // 3. Fetch Autocomplete Suggestions
    async function fetchAutocomplete(query) {
        if (!query) return;
        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            if (!res.ok) throw new Error('Search failed');
            const data = await res.json();
            renderAutocomplete(data);
        } catch (err) {
            console.error('Autocomplete fetch error:', err);
        }
    }

    // 4. Render Autocomplete Dropdown
    function renderAutocomplete(items) {
        autocompleteList.innerHTML = '';
        if (items.length === 0) {
            autocompleteList.classList.add('hidden');
            return;
        }

        items.forEach(item => {
            const li = document.createElement('li');
            li.className = 'autocomplete-item';
            
            let marketClass = 'ac-market-kospi';
            if (item.market === '코스닥') {
                marketClass = 'ac-market-kosdaq';
            } else if (item.market === 'NASDAQ' || item.market === 'NYSE' || item.market === 'US') {
                marketClass = 'ac-market-us';
            }
            
            li.innerHTML = `
                <div class="ac-name-wrapper">
                    <span class="ac-name">${item.name}</span>
                    <span class="ac-code">${item.code}</span>
                </div>
                <span class="ac-market ${marketClass}">${item.market}</span>
            `;
            
            li.addEventListener('click', () => {
                searchInput.value = item.name;
                autocompleteList.classList.add('hidden');
                loadStockPerformance(item.code);
            });
            
            autocompleteList.appendChild(li);
        });
        
        autocompleteList.classList.remove('hidden');
    }

    // 5. Trigger Search when Enter is hit or Popular Queries is clicked
    async function triggerSearch(query) {
        if (!query) return;
        autocompleteList.classList.add('hidden');
        showLoading(true);
        
        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            
            if (data.length > 0) {
                // If there's a match, load the first one
                searchInput.value = data[0].name;
                loadStockPerformance(data[0].code);
            } else {
                showLoading(false);
                alert(`'${query}'에 매칭되는 종목을 찾을 수 없습니다. 종목명이나 코드를 확인해 주세요.`);
            }
        } catch (err) {
            showLoading(false);
            console.error('Search trigger failed:', err);
            alert('종목 검색 도중 오류가 발생했습니다.');
        }
    }

    // 6. Fetch Stock Performance and Render Dashboard
    async function loadStockPerformance(code) {
        showLoading(true);
        welcomeView.classList.add('hidden');
        mainDashboard.classList.add('hidden');
        
        try {
            const res = await fetch(`/api/performance?code=${code}`);
            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.error || '실패');
            }
            const data = await res.json();
            
            // Set State
            rawChartData = data.chart;
            benchmarkSymbol = data.benchmark;
            rawOhlcData = data.ohlc || [];
            
            renderDashboard(data);
            
            // Save search to recent searches list
            saveToRecentSearches(data.stock.code, data.stock.name);
        } catch (err) {
            showLoading(false);
            welcomeView.classList.remove('hidden');
            alert(`수익률 로딩 오류: ${err.message}`);
        }
    }

    // 7. Toggle Loading Spinner
    function showLoading(isLoading) {
        if (isLoading) {
            spinner.classList.remove('hidden');
        } else {
            spinner.classList.add('hidden');
        }
    }

    // 8. Render Dashboard UI
    function renderDashboard(data) {
        // A. Set Header Meta
        stockNameEl.textContent = data.stock.name;
        stockCodeBadge.textContent = data.stock.code;
        
        marketBadge.textContent = data.stock.market;
        marketBadge.className = 'stock-badge ' + (data.stock.market === '코스피' ? 'market-badge-kospi' : 'market-badge-kosdaq');
        
        sectorBadge.textContent = data.stock.sector_name;
        
        // B. Populate Table
        renderPerformanceTable(data.table);
        
        // C. Render Sector Peers
        renderPeersList(data.peers);
        
        // D. Setup and Draw Chart
        renderChart(12); // Default to 12 months chart
        
        // E. Render Daily Candlestick Chart
        renderCandleChart();
        
        // Reset period buttons active state
        periodButtons.forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-months') === '12') {
                btn.classList.add('active');
            }
        });
        
        // Show Dashboard and Hide Spinner
        showLoading(false);
        mainDashboard.classList.remove('hidden');
    }

    // 9. Render Performance Table Helper
    function renderPerformanceTable(tableRows) {
        performanceTbody.innerHTML = '';
        
        tableRows.forEach(row => {
            const tr = document.createElement('tr');
            
            // Helpers to style performance returns
            const formatPct = (val) => `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
            const formatRelative = (val) => `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
            const getBadgeClass = (val) => val > 0 ? 'badge-pos' : (val < 0 ? 'badge-neg' : 'zero-val');
            const getMarketBadgeClass = (val) => val > 0 ? 'badge-market-pos' : (val < 0 ? 'badge-market-neg' : 'zero-val');
            
            const periodLabels = {
                '1D': '당일',
                '1W': '1주일',
                '1M': '1개월',
                '3M': '3개월',
                '6M': '6개월',
                '12M': '12개월'
            };
            
            const isWarningPeriod = ['1W', '1M', '3M', '6M', '12M'].includes(row.period);
            const isUnderperforming = isWarningPeriod && row.vs_market <= -5.0;
            
            let marketBadgeContent = '';
            if (isUnderperforming) {
                // Paint entire row soft red, and show glowing warning badge without coloring individual cell box red
                tr.classList.add('underperform-row');
                marketBadgeContent = `<span class="${getBadgeClass(row.vs_market)}">${formatRelative(row.vs_market)}</span> <span class="warning-badge">⚠️ 경고</span>`;
            } else {
                marketBadgeContent = `<span class="${getMarketBadgeClass(row.vs_market)}">${formatRelative(row.vs_market)}</span>`;
            }
            
            tr.innerHTML = `
                <td class="period-cell">${periodLabels[row.period] || row.period}</td>
                <td class="return-val"><span class="${getBadgeClass(row.stock_return)}">${formatPct(row.stock_return)}</span></td>
                <td class="relative-cell">${marketBadgeContent}</td>
                <td class="relative-cell"><span class="${getBadgeClass(row.vs_sector)}">${formatRelative(row.vs_sector)}</span></td>
            `;
            
            performanceTbody.appendChild(tr);
        });
    }

    // 9B. Helper to calculate Moving Averages (MA)
    function calculateMA(ohlcList, period) {
        const ma = [];
        for (let i = 0; i < ohlcList.length; i++) {
            if (i < period - 1) {
                ma.push({ x: ohlcList[i].date, y: null });
            } else {
                let sum = 0;
                for (let j = 0; j < period; j++) {
                    sum += ohlcList[i - j].close;
                }
                ma.push({ x: ohlcList[i].date, y: parseFloat((sum / period).toFixed(2)) });
            }
        }
        return ma;
    }

    // 9B-2. Helper to calculate MACD (12, 26, 9)
    function calculateMACD(ohlcList) {
        const closes = ohlcList.map(item => item.close);
        
        const getEMA = (prices, period) => {
            const k = 2 / (period + 1);
            const ema = [];
            let currentEma = prices[0] || 0;
            for (let i = 0; i < prices.length; i++) {
                if (i === 0) {
                    currentEma = prices[0] || 0;
                } else {
                    currentEma = prices[i] * k + currentEma * (1 - k);
                }
                ema.push(i < period - 1 ? null : parseFloat(currentEma.toFixed(4)));
            }
            return ema;
        };
        
        const ema12 = getEMA(closes, 12);
        const ema26 = getEMA(closes, 26);
        
        const macdLine = [];
        for (let i = 0; i < closes.length; i++) {
            if (ema12[i] === null || ema26[i] === null) {
                macdLine.push(null);
            } else {
                macdLine.push(parseFloat((ema12[i] - ema26[i]).toFixed(4)));
            }
        }
        
        const signalLine = [];
        const k9 = 2 / (9 + 1);
        let currentSignal = null;
        for (let i = 0; i < closes.length; i++) {
            if (macdLine[i] === null) {
                signalLine.push(null);
            } else {
                if (currentSignal === null) {
                    currentSignal = macdLine[i];
                    signalLine.push(null);
                } else {
                    currentSignal = macdLine[i] * k9 + currentSignal * (1 - k9);
                    signalLine.push(parseFloat(currentSignal.toFixed(4)));
                }
            }
        }
        
        // Nullify the first 8 valid MACD points of the Signal line to prevent starting bias
        let validMacdCount = 0;
        for (let i = 0; i < closes.length; i++) {
            if (macdLine[i] !== null) {
                validMacdCount++;
                if (validMacdCount < 9) {
                    signalLine[i] = null;
                }
            }
        }
        
        const histogram = [];
        for (let i = 0; i < closes.length; i++) {
            if (macdLine[i] === null || signalLine[i] === null) {
                histogram.push(null);
            } else {
                histogram.push(parseFloat((macdLine[i] - signalLine[i]).toFixed(4)));
            }
        }
        
        return {
            macd: macdLine,
            signal: signalLine,
            histogram: histogram
        };
    }

    // 9C. Render Daily Candlestick and Moving Averages
    function renderCandleChart() {
        const chartDiv = document.getElementById('candle-chart');
        if (!chartDiv) return;
        
        if (!rawOhlcData || rawOhlcData.length === 0) {
            chartDiv.innerHTML = '<div style="padding: 3rem; text-align: center; color: var(--text-secondary);">캔들 차트 데이터가 없거나 로딩 중입니다.</div>';
            return;
        }
        
        // Read user input days
        let daysToDisplay = 100; // default changed to 100 days
        const daysInput = document.getElementById('candle-days-input');
        if (daysInput) {
            const parsedVal = parseInt(daysInput.value);
            if (parsedVal >= 10 && parsedVal <= 400) {
                daysToDisplay = parsedVal;
            }
        }
        
        // Calculate Moving Averages (MA) on the complete dataset so the beginning of the display window is accurate!
        const ma5 = calculateMA(rawOhlcData, 5);
        const ma10 = calculateMA(rawOhlcData, 10);
        const ma20 = calculateMA(rawOhlcData, 20);
        const ma60 = calculateMA(rawOhlcData, 60);
        const ma120 = calculateMA(rawOhlcData, 120);
        const ma240 = calculateMA(rawOhlcData, 240);
        
        // Helper to format YYYYMMDD -> YYYY.MM.DD
        const formatDate = (str) => {
            if (!str) return str;
            const m = str.match(/^(\d{4})(\d{2})(\d{2})$/);
            return m ? `${m[1]}.${m[2]}.${m[3]}` : str;
        };

        // Format parameters for ApexCharts using full datasets to allow panning
        const candleSeriesData = rawOhlcData.map(item => ({
            x: formatDate(item.date),
            y: [item.open, item.high, item.low, item.close]
        }));
        
        const ma5SeriesData = ma5.map(item => ({ x: formatDate(item.x), y: item.y }));
        const ma10SeriesData = ma10.map(item => ({ x: formatDate(item.x), y: item.y }));
        const ma20SeriesData = ma20.map(item => ({ x: formatDate(item.x), y: item.y }));
        const ma60SeriesData = ma60.map(item => ({ x: formatDate(item.x), y: item.y }));
        const ma120SeriesData = ma120.map(item => ({ x: formatDate(item.x), y: item.y }));
        const ma240SeriesData = ma240.map(item => ({ x: formatDate(item.x), y: item.y }));
        
        // Destroy past charts to prevent double-draw instances
        if (candleChartInstance) {
            candleChartInstance.destroy();
            candleChartInstance = null;
        }
        if (volumeChartInstance) {
            volumeChartInstance.destroy();
            volumeChartInstance = null;
        }
        if (macdChartInstance) {
            macdChartInstance.destroy();
            macdChartInstance = null;
        }
        
        // Detect crossovers and prepare annotations
        const detectCrosses = (short, long, name) => {
            const points = [];
            for (let i = 1; i < short.length; i++) {
                const prevShort = short[i - 1].y;
                const prevLong = long[i - 1].y;
                const curShort = short[i].y;
                const curLong = long[i].y;
                if (prevShort == null || prevLong == null || curShort == null || curLong == null) continue;
                const isGolden = prevShort < prevLong && curShort > curLong;
                const isDead = prevShort > prevLong && curShort < curLong;
                if (isGolden || isDead) {
                    const labelText = `${name} ${isGolden ? 'golden' : 'dead'}`;
                    const labelColor = isGolden ? '#d97706' : '#7c3aed';
                    const labelBg = isGolden ? '#fef3c7' : '#ede9fe';
                    points.push({
                        x: formatDate(short[i].x),
                        y: curShort,
                        marker: {
                            size: 5,
                            fillColor: labelColor,
                            strokeColor: labelColor,
                            strokeWidth: 1,
                            shape: 'circle'
                        },
                        label: {
                            text: labelText,
                            offsetY: isGolden ? 40 : -40,
                            borderColor: labelColor,
                            borderWidth: 1,
                            borderRadius: 4,
                            style: {
                                color: labelColor,
                                background: labelBg,
                                fontSize: '10px',
                                fontWeight: 700,
                                padding: { top: 3, bottom: 3, left: 6, right: 6 }
                            }
                        }
                    });
                }
            }
            return points;
        };
        const annotations = [];
        // Detect crosses on full datasets so annotations are visible when panning
        annotations.push(...detectCrosses(ma5, ma20, '5/20'));
        annotations.push(...detectCrosses(ma5, ma60, '5/60'));
        annotations.push(...detectCrosses(ma20, ma60, '20/60'));

        // Prepare Volume series data
        const volumeSeriesData = rawOhlcData.map(item => ({
            x: formatDate(item.date),
            y: item.volume
        }));

        // Prepare MACD series data
        const macdData = calculateMACD(rawOhlcData);
        const macdSeriesData = macdData.macd.map((val, idx) => ({
            x: formatDate(rawOhlcData[idx].date),
            y: val
        }));
        const signalSeriesData = macdData.signal.map((val, idx) => ({
            x: formatDate(rawOhlcData[idx].date),
            y: val
        }));
        const histogramSeriesData = macdData.histogram.map((val, idx) => ({
            x: formatDate(rawOhlcData[idx].date),
            y: val
        }));

        // 1. Candlestick Chart Options
        const candleOptions = {
            series: [
                {
                    name: '일봉 캔들',
                    type: 'candlestick',
                    data: candleSeriesData
                },
                {
                    name: '5일선',
                    type: 'line',
                    data: ma5SeriesData
                },
                {
                    name: '10일선',
                    type: 'line',
                    data: ma10SeriesData
                },
                {
                    name: '20일선',
                    type: 'line',
                    data: ma20SeriesData
                },
                {
                    name: '60일선',
                    type: 'line',
                    data: ma60SeriesData
                },
                {
                    name: '120일선',
                    type: 'line',
                    data: ma120SeriesData
                },
                {
                    name: '240일선',
                    type: 'line',
                    data: ma240SeriesData
                }
            ],
            annotations: { points: annotations },
            chart: {
                id: 'candle-chart',
                group: 'stock-charts',
                height: 320,
                type: 'line',
                zoom: {
                    enabled: true,
                    type: 'x',
                    autoScaleYaxis: true,
                    allowMouseWheelZoom: false
                },
                toolbar: {
                    show: false,
                    autoSelected: 'pan',
                    tools: {
                        download: false,
                        selection: false,
                        zoom: false,
                        zoomin: false,
                        zoomout: false,
                        pan: true,
                        reset: false
                    }
                },
                animations: {
                    enabled: false
                },
                fontFamily: 'Outfit, Inter, sans-serif'
            },
            plotOptions: {
                candlestick: {
                    colors: {
                        upward: '#dc2626',   // 양봉 (Red)
                        downward: '#2563eb'  // 음봉 (Blue)
                    },
                    wick: {
                        useFillColor: true
                    }
                }
            },
            stroke: {
                width: [1, 1.5, 1.5, 1.5, 2, 2.2, 2.5],
                curve: 'smooth'
            },
            colors: [
                '#808080', // Candle base outline placeholder color
                '#eab308', // MA5: Gold
                '#f97316', // MA10: Orange
                '#ec4899', // MA20: Pink
                '#10b981', // MA60: Green
                '#8b5cf6', // MA120: Purple
                '#64748b'  // MA240: Slate
            ],
            xaxis: {
                type: 'category',
                min: Math.max(1, rawOhlcData.length - daysToDisplay + 1),
                max: rawOhlcData.length,
                labels: {
                    show: false // Hide X-axis labels to avoid duplication
                },
                axisBorder: { show: false },
                axisTicks: { show: false },
                tooltip: { enabled: false }
            },
            yaxis: {
                labels: {
                    minWidth: 80,
                    formatter: function(val) {
                        const isUS = !/^[0-9]+$/.test(stockCodeBadge.textContent);
                        return isUS ? '$' + val.toFixed(2) : val.toLocaleString() + '원';
                    },
                    style: {
                        colors: '#64748b',
                        fontSize: '11px',
                        fontWeight: 500
                    }
                }
            },
            tooltip: {
                shared: true,
                custom: function({ seriesIndex, dataPointIndex, w }) {
                    const ohlc = w.config.series[0].data[dataPointIndex];
                    if (!ohlc) return '';
                    
                    const date = ohlc.x;
                    const [open, high, low, close] = ohlc.y;
                    
                    const isUS = !/^[0-9]+$/.test(stockCodeBadge.textContent);
                    const formatPrice = (p) => isUS ? '$' + p.toFixed(2) : p.toLocaleString() + '원';
                    
                    let html = `<div class="apexcharts-custom-tooltip" style="padding: 10px; font-family: 'Outfit'; font-size: 12px; background: rgba(255,255,255,0.95); border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">`;
                    html += `<div style="font-weight: 700; color: #1e293b; margin-bottom: 6px;">📅 날짜: ${date}</div>`;
                    html += `<div style="display: grid; grid-template-columns: auto auto; gap: 4px 15px; color: #475569;">`;
                    html += `<span>시가:</span><span style="font-weight:600; text-align:right;">${formatPrice(open)}</span>`;
                    html += `<span>고가:</span><span style="font-weight:600; text-align:right; color:#dc2626;">${formatPrice(high)}</span>`;
                    html += `<span>저가:</span><span style="font-weight:600; text-align:right; color:#2563eb;">${formatPrice(low)}</span>`;
                    html += `<span>종가:</span><span style="font-weight:600; text-align:right; color:#1e293b;">${formatPrice(close)}</span>`;
                    
                    for (let s = 1; s < w.config.series.length; s++) {
                        const val = w.config.series[s].data[dataPointIndex].y;
                        if (val !== null) {
                            html += `<span>${w.config.series[s].name}:</span><span style="font-weight:600; text-align:right; color:${w.config.colors[s]};">${formatPrice(val)}</span>`;
                        }
                    }
                    html += `</div></div>`;
                    return html;
                }
            },
            legend: {
                position: 'top',
                horizontalAlign: 'center',
                labels: {
                    colors: '#475569'
                }
            }
        };

        // 2. Volume Chart Options
        const volumeOptions = {
            series: [
                {
                    name: '거래량',
                    data: volumeSeriesData
                }
            ],
            chart: {
                id: 'volume-chart',
                group: 'stock-charts',
                height: 140,
                type: 'bar',
                zoom: {
                    enabled: true,
                    type: 'x',
                    allowMouseWheelZoom: false
                },
                toolbar: {
                    show: false,
                    autoSelected: 'pan',
                    tools: {
                        download: false,
                        selection: false,
                        zoom: false,
                        zoomin: false,
                        zoomout: false,
                        pan: true,
                        reset: false
                    }
                },
                animations: {
                    enabled: false
                },
                fontFamily: 'Outfit, Inter, sans-serif'
            },
            plotOptions: {
                bar: {
                    columnWidth: '80%'
                }
            },
            fill: {
                colors: [
                    function({ value, dataPointIndex, w }) {
                        const item = rawOhlcData[dataPointIndex];
                        if (!item) return '#808080';
                        return item.close >= item.open ? '#dc2626' : '#2563eb';
                    }
                ]
            },
            xaxis: {
                type: 'category',
                min: Math.max(1, rawOhlcData.length - daysToDisplay + 1),
                max: rawOhlcData.length,
                labels: {
                    show: false // Hide X-axis labels to avoid duplication
                },
                axisBorder: { show: false },
                axisTicks: { show: false },
                tooltip: { enabled: false }
            },
            yaxis: {
                labels: {
                    minWidth: 80,
                    formatter: function(val) {
                        if (val >= 1000000) {
                            return (val / 1000000).toFixed(1) + 'M';
                        } else if (val >= 1000) {
                            return (val / 1000).toFixed(0) + 'K';
                        }
                        return val.toLocaleString();
                    },
                    style: {
                        colors: '#64748b',
                        fontSize: '11px',
                        fontWeight: 500
                    }
                }
            },
            tooltip: {
                shared: true,
                custom: function({ seriesIndex, dataPointIndex, w }) {
                    const item = rawOhlcData[dataPointIndex];
                    if (!item) return '';
                    const date = formatDate(item.date);
                    let html = `<div class="apexcharts-custom-tooltip" style="padding: 10px; font-family: 'Outfit'; font-size: 12px; background: rgba(255,255,255,0.95); border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">`;
                    html += `<div style="font-weight: 700; color: #1e293b; margin-bottom: 4px;">📅 날짜: ${date}</div>`;
                    html += `<div style="color: #475569;">거래량: <span style="font-weight:600; color:#1e293b;">${item.volume.toLocaleString()}주</span></div>`;
                    html += `</div>`;
                    return html;
                }
            },
            legend: {
                show: false
            }
        };

        // 3. MACD Chart Options
        const macdOptions = {
            series: [
                {
                    name: 'MACD',
                    type: 'line',
                    data: macdSeriesData
                },
                {
                    name: 'Signal',
                    type: 'line',
                    data: signalSeriesData
                },
                {
                    name: 'Histogram',
                    type: 'bar',
                    data: histogramSeriesData
                }
            ],
            chart: {
                id: 'macd-chart',
                group: 'stock-charts',
                height: 160,
                type: 'line',
                zoom: {
                    enabled: true,
                    type: 'x',
                    allowMouseWheelZoom: false
                },
                toolbar: {
                    show: false,
                    autoSelected: 'pan',
                    tools: {
                        download: false,
                        selection: false,
                        zoom: false,
                        zoomin: false,
                        zoomout: false,
                        pan: true,
                        reset: false
                    }
                },
                animations: {
                    enabled: false
                },
                fontFamily: 'Outfit, Inter, sans-serif'
            },
            plotOptions: {
                bar: {
                    columnWidth: '80%'
                }
            },
            stroke: {
                width: [1.5, 1.5, 0],
                curve: 'smooth'
            },
            colors: [
                '#0284c7', // MACD: Slate/Cyanish Blue
                '#f59e0b', // Signal: Orange/Amber
                '#b91c1c'  // Histogram baseline fallback
            ],
            fill: {
                colors: [
                    '#0284c7',
                    '#f59e0b',
                    function({ value, dataPointIndex, w }) {
                        return value >= 0 ? '#dc2626' : '#2563eb';
                    }
                ]
            },
            xaxis: {
                type: 'category',
                min: Math.max(1, rawOhlcData.length - daysToDisplay + 1),
                max: rawOhlcData.length,
                labels: {
                    style: {
                        colors: '#64748b',
                        fontSize: '11px',
                        fontWeight: 500
                    },
                    rotate: -45,
                    rotateAlways: false
                },
                tickAmount: Math.min(10, daysToDisplay)
            },
            yaxis: {
                labels: {
                    minWidth: 80,
                    formatter: function(val) {
                        return val !== null ? val.toFixed(2) : '';
                    },
                    style: {
                        colors: '#64748b',
                        fontSize: '11px',
                        fontWeight: 500
                    }
                }
            },
            tooltip: {
                shared: true,
                custom: function({ seriesIndex, dataPointIndex, w }) {
                    const item = rawOhlcData[dataPointIndex];
                    if (!item) return '';
                    const date = formatDate(item.date);
                    const macdVal = macdSeriesData[dataPointIndex].y;
                    const signalVal = signalSeriesData[dataPointIndex].y;
                    const histVal = histogramSeriesData[dataPointIndex].y;
                    
                    let html = `<div class="apexcharts-custom-tooltip" style="padding: 10px; font-family: 'Outfit'; font-size: 12px; background: rgba(255,255,255,0.95); border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">`;
                    html += `<div style="font-weight: 700; color: #1e293b; margin-bottom: 6px;">📅 날짜: ${date}</div>`;
                    html += `<div style="display: grid; grid-template-columns: auto auto; gap: 4px 15px; color: #475569;">`;
                    if (macdVal !== null) {
                        html += `<span>MACD:</span><span style="font-weight:600; text-align:right; color:#0284c7;">${macdVal.toFixed(2)}</span>`;
                    }
                    if (signalVal !== null) {
                        html += `<span>Signal:</span><span style="font-weight:600; text-align:right; color:#f59e0b;">${signalVal.toFixed(2)}</span>`;
                    }
                    if (histVal !== null) {
                        const histColor = histVal >= 0 ? '#dc2626' : '#2563eb';
                        html += `<span>Histogram:</span><span style="font-weight:600; text-align:right; color:${histColor};">${histVal.toFixed(2)}</span>`;
                    }
                    html += `</div></div>`;
                    return html;
                }
            },
            legend: {
                position: 'top',
                horizontalAlign: 'center',
                labels: {
                    colors: '#475569'
                }
            }
        };

        // Render All Synchronized Charts
        candleChartInstance = new ApexCharts(document.getElementById('candle-chart'), candleOptions);
        candleChartInstance.render();

        volumeChartInstance = new ApexCharts(document.getElementById('volume-chart'), volumeOptions);
        volumeChartInstance.render();

        macdChartInstance = new ApexCharts(document.getElementById('macd-chart'), macdOptions);
        macdChartInstance.render();
    }

    // 10. Render Peer Badges
    function renderPeersList(peers) {
        peersListContainer.innerHTML = '';
        if (peers.length === 0) {
            peersListContainer.innerHTML = '<span class="peer-tag">동종 업종 종목 없음</span>';
            return;
        }
        
        peers.forEach(peer => {
            const span = document.createElement('span');
            span.className = 'peer-tag';
            
            // Support both object and string format (US stock vs Korean stock peers)
            const peerName = typeof peer === 'object' ? peer.name : peer;
            const peerCode = typeof peer === 'object' ? peer.code : peer;
            
            span.textContent = peerName;
            span.addEventListener('click', () => {
                searchInput.value = peerName;
                loadStockPerformance(peerCode);
            });
            peersListContainer.appendChild(span);
        });
    }

    // 11. Chart Period Selectors Click Event
    periodButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            periodButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const months = parseInt(btn.getAttribute('data-months'));
            renderChart(months);
        });
    });

    // 11B. Candlestick Chart Duration Control listeners
    const candleDaysInput = document.getElementById('candle-days-input');
    const updateCandleBtn = document.getElementById('update-candle-btn');
    if (updateCandleBtn) {
        updateCandleBtn.addEventListener('click', () => {
            renderCandleChart();
        });
    }
    if (candleDaysInput) {
        candleDaysInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                renderCandleChart();
            }
        });
    }

    // 12. Render Interactive Comparative Chart
    function renderChart(months) {
        if (!rawChartData || !rawChartData.dates.length) return;
        
        // A. Calculate Slicing Indexes
        let tradingDays = 250; // default to 1 year
        if (months === 6) tradingDays = 120;
        else if (months === 3) tradingDays = 60;
        else if (months === 1) tradingDays = 20;
        
        const len = rawChartData.dates.length;
        const startIdx = Math.max(0, len - tradingDays);
        
        const datesSlice = rawChartData.dates.slice(startIdx);
        const stockSlice = rawChartData.stock.slice(startIdx);
        const marketSlice = rawChartData.market.slice(startIdx);
        const sectorSlice = rawChartData.sector.slice(startIdx);
        
        // B. Re-normalize to 100% on the start date of this sub-period
        const stockBase = stockSlice[0];
        const marketBase = marketSlice[0];
        const sectorBase = sectorSlice[0];
        
        const normStock = stockSlice.map(v => stockBase ? (v / stockBase) * 100 : 100);
        const normMarket = marketSlice.map(v => marketBase ? (v / marketBase) * 100 : 100);
        const normSector = sectorSlice.map(v => sectorBase ? (v / sectorBase) * 100 : 100);
        
        // C. Clean and recreate Chart canvas
        const ctx = document.getElementById('relative-chart').getContext('2d');
        
        if (relativeChart) {
            relativeChart.destroy();
        }
        
        // D. Create beautiful gradient objects for lines
        const stockGrad = ctx.createLinearGradient(0, 0, 0, 300);
        stockGrad.addColorStop(0, 'rgba(6, 182, 212, 0.18)');
        stockGrad.addColorStop(1, 'rgba(6, 182, 212, 0.0)');
        
        const sectorGrad = ctx.createLinearGradient(0, 0, 0, 300);
        sectorGrad.addColorStop(0, 'rgba(168, 85, 247, 0.15)');
        sectorGrad.addColorStop(1, 'rgba(168, 85, 247, 0.0)');

        // E. Chart.js Config
        relativeChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: datesSlice,
                datasets: [
                    {
                        label: '종목 (Stock)',
                        data: normStock,
                        borderColor: '#06b6d4',
                        borderWidth: 2.5,
                        backgroundColor: stockGrad,
                        fill: true,
                        tension: 0.15,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        pointHoverBackgroundColor: '#06b6d4',
                        pointHoverBorderColor: '#ffffff',
                        pointHoverBorderWidth: 1.5
                    },
                    {
                        label: `업종 평균 (Sector Avg)`,
                        data: normSector,
                        borderColor: '#a855f7',
                        borderWidth: 2,
                        backgroundColor: sectorGrad,
                        fill: true,
                        tension: 0.15,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        pointHoverBackgroundColor: '#a855f7',
                        pointHoverBorderColor: '#ffffff',
                        pointHoverBorderWidth: 1.5
                    },
                    {
                        label: `지수 (${benchmarkSymbol})`,
                        data: normMarket,
                        borderColor: '#3b82f6',
                        borderWidth: 1.5,
                        borderDash: [4, 4],
                        backgroundColor: 'transparent',
                        fill: false,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        pointHoverBackgroundColor: '#3b82f6',
                        pointHoverBorderColor: '#ffffff',
                        pointHoverBorderWidth: 1.5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#475569',
                            font: {
                                family: 'Inter',
                                size: 11
                            },
                            boxWidth: 12,
                            boxHeight: 6,
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.98)',
                        titleColor: '#0f172a',
                        bodyColor: '#334155',
                        borderColor: 'rgba(0, 0, 0, 0.08)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: {
                            family: 'Outfit',
                            weight: '600'
                        },
                        bodyFont: {
                            family: 'Inter'
                        },
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += `${context.parsed.y.toFixed(2)}%`;
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.04)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#64748b',
                            font: {
                                size: 10,
                                family: 'Outfit'
                            },
                            maxRotation: 0,
                            autoSkip: true,
                            autoSkipPadding: 40
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.04)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#64748b',
                            font: {
                                size: 10,
                                family: 'Outfit'
                            },
                            callback: function(value) {
                                return value.toFixed(0) + '%';
                            }
                        }
                    }
                }
            }
        });
    }
});
