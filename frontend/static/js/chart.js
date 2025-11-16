// 全域變數
let priceChart = null;
let volumeChart = null;
let currentDate = null;
let currentStock = null;
let allTradesData = []; // 保存所有成交明細資料用於點擊查找
let allDepthHistory = []; // 保存完整的五檔歷史資料
let allTimeline = []; // 統一時間軸（合併 Trade 和 Depth 的所有時間戳）
let isUserScrolling = false; // 標記用戶是否正在手動滾動
let scrollTimeout = null;
let isPlaying = false; // 是否正在播放
let playbackInterval = null; // 播放計時器
let currentTimelineIndex = 0; // 當前時間軸位置（基於 allTimeline）
let currentTime = null; // 當前時間（Date 對象）

// 圖表時間軸相關變數
let allChartData = { labels: [], prices: [], volumes: [], timestamps: [] }; // 完整圖表資料
let chartWindowSize = 100; // 窗口大小（百分比）
let chartWindowStart = 0; // 窗口起始位置（百分比）

// 拖曳選取相關變數
let isDragging = false;
let dragStartX = 0;
let dragEndX = 0;
let dragStartIndex = 0;
let dragEndIndex = 0;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    loadDates();
    setupEventListeners();
});

// 設定事件監聽
function setupEventListeners() {
    document.getElementById('dateSelect').addEventListener('change', onDateChange);
    document.getElementById('stockSelect').addEventListener('change', onStockChange);
    document.getElementById('refreshBtn').addEventListener('click', refreshData);

    // 添加成交明細滾動監聽
    const tradesContainer = document.querySelector('.trades-container');
    if (tradesContainer) {
        tradesContainer.addEventListener('scroll', onTradesScroll);
    }

    // 添加時間軸滑桿事件
    const timelineSlider = document.getElementById('timelineSlider');
    if (timelineSlider) {
        timelineSlider.addEventListener('input', onTimelineChange);
    }

    // 添加播放/暫停按鈕事件
    const playPauseBtn = document.getElementById('playPauseBtn');
    if (playPauseBtn) {
        playPauseBtn.addEventListener('click', togglePlayback);
    }

    // 添加圖表時間軸控制事件
    const chartTimelineSlider = document.getElementById('chartTimelineSlider');
    if (chartTimelineSlider) {
        chartTimelineSlider.addEventListener('input', onChartTimelineChange);
    }

    const zoomInBtn = document.getElementById('zoomInBtn');
    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', zoomInChart);
    }

    const zoomOutBtn = document.getElementById('zoomOutBtn');
    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', zoomOutChart);
    }

    const resetZoomBtn = document.getElementById('resetZoomBtn');
    if (resetZoomBtn) {
        resetZoomBtn.addEventListener('click', resetChartZoom);
    }

    // 添加鍵盤快捷鍵
    document.addEventListener('keydown', handleKeyboardShortcuts);

    // 添加圖表拖曳選取功能
    const priceChartCanvas = document.getElementById('priceChart');
    if (priceChartCanvas) {
        priceChartCanvas.addEventListener('mousedown', onChartDragStart);
        priceChartCanvas.addEventListener('mousemove', onChartDragMove);
        priceChartCanvas.addEventListener('mouseup', onChartDragEnd);
        priceChartCanvas.addEventListener('mouseleave', onChartDragEnd);
    }
}

// 圖表拖曳開始
function onChartDragStart(event) {
    // 只在按住 Shift 鍵時啟用拖曳選取
    if (!event.shiftKey) {
        return;
    }

    const rect = event.target.getBoundingClientRect();
    dragStartX = event.clientX - rect.left;
    isDragging = true;
    event.target.style.cursor = 'crosshair';
}

// 圖表拖曳移動
function onChartDragMove(event) {
    if (!isDragging) {
        // 顯示提示：按住 Shift 拖曳選取時間範圍
        if (event.shiftKey) {
            event.target.style.cursor = 'crosshair';
        } else {
            event.target.style.cursor = 'pointer';
        }
        return;
    }

    const rect = event.target.getBoundingClientRect();
    dragEndX = event.clientX - rect.left;

    // TODO: 顯示選取範圍的視覺反饋
}

// 圖表拖曳結束
function onChartDragEnd(event) {
    if (!isDragging) {
        return;
    }

    isDragging = false;
    event.target.style.cursor = 'pointer';

    const rect = event.target.getBoundingClientRect();
    dragEndX = event.clientX - rect.left;

    // 計算選取範圍
    if (Math.abs(dragEndX - dragStartX) < 10) {
        // 拖曳距離太小，視為點擊
        return;
    }

    // 轉換像素位置到資料索引
    const chartWidth = rect.width;
    const totalPoints = allChartData.timestamps.length;
    const currentStartIndex = Math.floor((chartWindowStart / 100) * totalPoints);
    const currentEndIndex = Math.min(
        Math.ceil(((chartWindowStart + chartWindowSize) / 100) * totalPoints),
        totalPoints
    );
    const visiblePoints = currentEndIndex - currentStartIndex;

    // 計算選取範圍的索引
    let startIndex = currentStartIndex + Math.floor((Math.min(dragStartX, dragEndX) / chartWidth) * visiblePoints);
    let endIndex = currentStartIndex + Math.ceil((Math.max(dragStartX, dragEndX) / chartWidth) * visiblePoints);

    // 限制範圍
    startIndex = Math.max(0, Math.min(startIndex, totalPoints - 1));
    endIndex = Math.max(0, Math.min(endIndex, totalPoints - 1));

    if (startIndex >= endIndex) {
        return;
    }

    // 更新圖表窗口
    chartWindowStart = (startIndex / totalPoints) * 100;
    chartWindowSize = ((endIndex - startIndex) / totalPoints) * 100;

    // 確保窗口大小不小於 10%
    chartWindowSize = Math.max(10, chartWindowSize);

    // 更新顯示
    updateChartDisplay();
    updateChartTimelineLabels();

    // 更新滑桿
    const chartTimelineSlider = document.getElementById('chartTimelineSlider');
    if (chartTimelineSlider) {
        const maxStart = 100 - chartWindowSize;
        chartTimelineSlider.max = maxStart;
        chartTimelineSlider.value = chartWindowStart;
    }
}

// 處理鍵盤快捷鍵
function handleKeyboardShortcuts(event) {
    // 如果焦點在輸入框內，不處理快捷鍵
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'SELECT' || event.target.tagName === 'TEXTAREA') {
        return;
    }

    switch(event.key) {
        case 'ArrowUp':
            // 上鍵：向前瀏覽（較新的交易）
            event.preventDefault();
            navigateTrade(-1);
            break;
        case 'ArrowDown':
            // 下鍵：向後瀏覽（較舊的交易）
            event.preventDefault();
            navigateTrade(1);
            break;
        case ' ':
            // 空白鍵：播放/暫停
            event.preventDefault();
            const playPauseBtn = document.getElementById('playPauseBtn');
            if (playPauseBtn && playPauseBtn.style.display !== 'none') {
                togglePlayback();
            }
            break;
    }
}

// 導航到上一筆/下一筆（時間軸移動）
function navigateTrade(direction) {
    if (allTimeline.length === 0) {
        return;
    }

    // 停止播放
    if (isPlaying) {
        togglePlayback();
    }

    // 計算新的索引
    let newIndex = currentTimelineIndex + direction;

    // 限制範圍
    newIndex = Math.max(0, Math.min(newIndex, allTimeline.length - 1));

    if (newIndex !== currentTimelineIndex) {
        currentTimelineIndex = newIndex;

        // 更新時間軸滑桿
        const timelineSlider = document.getElementById('timelineSlider');
        if (timelineSlider) {
            const percentage = (currentTimelineIndex / (allTimeline.length - 1)) * 100;
            timelineSlider.value = percentage;
        }

        // 更新顯示
        updateByTimelineIndex(currentTimelineIndex);
    }
}

// 初始化圖表
function initCharts() {
    const priceCtx = document.getElementById('priceChart').getContext('2d');
    const volumeCtx = document.getElementById('volumeChart').getContext('2d');

    // 價格走勢圖
    priceChart = new Chart(priceCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '價格',
                data: [],
                borderColor: '#ffcc00',
                backgroundColor: 'rgba(255, 204, 0, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.1,
                order: 1
            }, {
                label: 'VWAP',
                data: [],
                borderColor: '#00ff00',
                backgroundColor: 'transparent',
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.1,
                borderDash: [5, 5],
                order: 2
            }, {
                label: '當前位置',
                data: [],
                borderColor: '#ff0000',
                backgroundColor: '#ff0000',
                pointRadius: 8,
                pointHoverRadius: 10,
                showLine: false,
                order: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#ffffff'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        stepSize: 1,
                        displayFormats: {
                            minute: 'HH:mm',
                            second: 'HH:mm:ss'
                        }
                    },
                    ticks: {
                        color: '#999',
                        autoSkip: true,
                        maxRotation: 45,
                        minRotation: 0
                    },
                    grid: {
                        color: '#333'
                    }
                },
                y: {
                    ticks: {
                        color: '#999'
                    },
                    grid: {
                        color: '#333'
                    }
                }
            },
            onClick: (event, activeElements) => {
                if (activeElements.length > 0) {
                    const visibleIndex = activeElements[0].index;
                    // 轉換可見窗口索引到完整資料索引
                    const totalPoints = allChartData.timestamps.length;
                    const startIndex = Math.floor((chartWindowStart / 100) * totalPoints);
                    const actualIndex = startIndex + visibleIndex;
                    scrollToTradeByIndex(actualIndex);
                }
            },
            onHover: (event, activeElements) => {
                event.native.target.style.cursor = activeElements.length > 0 ? 'pointer' : 'default';
            }
        }
    });

    // 成交量圖
    volumeChart = new Chart(volumeCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: '成交量',
                data: [],
                backgroundColor: '#9933cc',
                borderColor: '#9933cc',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#ffffff'
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        stepSize: 1,
                        displayFormats: {
                            minute: 'HH:mm',
                            second: 'HH:mm:ss'
                        }
                    },
                    ticks: {
                        color: '#999',
                        autoSkip: true,
                        maxRotation: 45,
                        minRotation: 0
                    },
                    grid: {
                        color: '#333'
                    }
                },
                y: {
                    ticks: {
                        color: '#999'
                    },
                    grid: {
                        color: '#333'
                    }
                }
            }
        }
    });
}

// 載入日期列表
async function loadDates() {
    try {
        const response = await axios.get('/api/dates');
        const dates = response.data;

        const dateSelect = document.getElementById('dateSelect');
        dateSelect.innerHTML = '<option value="">選擇日期...</option>';

        dates.forEach(date => {
            const option = document.createElement('option');
            option.value = date;
            option.textContent = formatDate(date);
            dateSelect.appendChild(option);
        });
    } catch (error) {
        console.error('載入日期失敗:', error);
        alert('載入日期失敗，請檢查伺服器是否正常運行');
    }
}

// 日期變更事件
async function onDateChange(event) {
    const date = event.target.value;
    if (!date) {
        return;
    }

    currentDate = date;
    await loadStocks(date);
}

// 載入股票列表
async function loadStocks(date) {
    try {
        const response = await axios.get(`/api/stocks/${date}`);
        const stocks = response.data;

        const stockSelect = document.getElementById('stockSelect');
        stockSelect.innerHTML = '<option value="">選擇股票...</option>';

        stocks.forEach(stock => {
            const option = document.createElement('option');
            option.value = stock;
            option.textContent = stock;
            stockSelect.appendChild(option);
        });

        // 隱藏股票資訊
        document.getElementById('stockInfo').style.display = 'none';
    } catch (error) {
        console.error('載入股票失敗:', error);
        alert('載入股票失敗');
    }
}

// 股票變更事件
async function onStockChange(event) {
    const stock = event.target.value;
    if (!stock || !currentDate) {
        return;
    }

    currentStock = stock;
    await loadStockData(currentDate, stock);
}

// 載入股票資料
async function loadStockData(date, stock) {
    try {
        const response = await axios.get(`/api/data/${date}/${stock}`);
        const data = response.data;

        // 顯示統計資訊
        displayStatistics(data.stats, stock);

        // 更新圖表
        updateCharts(data.chart);

        // 更新五檔
        updateDepth(data.depth);

        // 更新成交明細
        updateTrades(data.trades);

        // 顯示股票資訊
        document.getElementById('stockInfo').style.display = 'block';

        // 自動載入完整的五檔歷史（用於回放時更新五檔）
        await loadDepthHistoryData(date, stock);

        // 初始化時間軸控制
        initializeTimeline();

        // 啟用滾動監聽
        isUserScrolling = true;
    } catch (error) {
        console.error('載入股票資料失敗:', error);
        alert('載入股票資料失敗');
    }
}

// 顯示統計資訊
function displayStatistics(stats, stockCode) {
    if (!stats) {
        return;
    }

    document.getElementById('stockCode').textContent = stockCode;
    document.getElementById('stockName').textContent = stockCode; // 可以加入股票名稱對照

    const currentPrice = stats.current_price.toFixed(2);
    const change = stats.change.toFixed(2);
    const changePct = stats.change_pct.toFixed(2);

    document.getElementById('currentPrice').textContent = currentPrice;
    document.getElementById('priceChange').textContent = (change >= 0 ? '+' : '') + change;
    document.getElementById('priceChangePct').textContent = (changePct >= 0 ? '+' : '') + changePct + '%';

    // 設定漲跌顏色
    const priceClass = change >= 0 ? 'up' : 'down';
    document.getElementById('currentPrice').className = `price ${priceClass}`;
    document.getElementById('priceChange').className = `change ${priceClass}`;
    document.getElementById('priceChangePct').className = `change-pct ${priceClass}`;

    document.getElementById('totalVolume').textContent = (stats.total_volume / 1000).toFixed(0);
    document.getElementById('highPrice').textContent = stats.high_price.toFixed(2);
    document.getElementById('lowPrice').textContent = stats.low_price.toFixed(2);
    document.getElementById('openPrice').textContent = stats.open_price.toFixed(2);
    document.getElementById('avgPrice').textContent = stats.avg_price.toFixed(2);
}

// 更新圖表
function updateCharts(chartData) {
    if (!chartData) {
        return;
    }

    // 保存完整的圖表資料（使用原始時間戳，不轉換為字串）
    allChartData = {
        timestamps: chartData.timestamps,
        prices: chartData.prices,
        volumes: chartData.volumes,
        vwap: chartData.vwap || []  // 添加 VWAP 資料
    };

    // 重置圖表窗口
    chartWindowSize = 100;
    chartWindowStart = 0;

    // 更新圖表顯示
    updateChartDisplay();

    // 初始化圖表時間軸控制
    initializeChartTimeline();
}

// 更新圖表顯示（根據窗口）
function updateChartDisplay() {
    if (!allChartData || !allChartData.timestamps || allChartData.timestamps.length === 0) {
        return;
    }

    const totalPoints = allChartData.timestamps.length;
    const startIndex = Math.floor((chartWindowStart / 100) * totalPoints);
    const endIndex = Math.min(
        Math.ceil(((chartWindowStart + chartWindowSize) / 100) * totalPoints),
        totalPoints
    );

    // 提取窗口範圍內的資料並轉換為 {x, y} 格式
    const priceData = [];
    const volumeData = [];
    const vwapData = [];

    for (let i = startIndex; i < endIndex; i++) {
        const timestamp = allChartData.timestamps[i];

        // 價格資料
        if (allChartData.prices[i] !== null && allChartData.prices[i] !== undefined) {
            priceData.push({ x: timestamp, y: allChartData.prices[i] });
        }

        // 成交量資料
        if (allChartData.volumes[i] !== null && allChartData.volumes[i] !== undefined) {
            volumeData.push({ x: timestamp, y: allChartData.volumes[i] });
        }

        // VWAP 資料
        if (allChartData.vwap && allChartData.vwap[i] !== null && allChartData.vwap[i] !== undefined) {
            vwapData.push({ x: timestamp, y: allChartData.vwap[i] });
        }
    }

    // 更新價格圖
    priceChart.data.datasets[0].data = priceData;
    if (priceChart.data.datasets.length > 1) {
        priceChart.data.datasets[1].data = vwapData;  // VWAP 線
    }
    // 保留第三個 dataset（當前位置紅點），不清除
    priceChart.update();

    // 更新成交量圖
    volumeChart.data.datasets[0].data = volumeData;
    volumeChart.update();
}

// 更新五檔報價
function updateDepth(depthData) {
    const tbody = document.getElementById('depthTableBody');

    if (!depthData || (!depthData.bids.length && !depthData.asks.length)) {
        tbody.innerHTML = '<tr><td colspan="3" class="no-data">暫無資料</td></tr>';
        return;
    }

    // 更新時間顯示
    const timestampElem = document.getElementById('depthTimestamp');
    if (timestampElem && depthData.timestamp) {
        timestampElem.textContent = `@ ${formatTime(depthData.timestamp)}`;
    }

    // 確保有五檔
    const bids = depthData.bids.slice(0, 5);
    const asks = depthData.asks.slice(0, 5);

    // 計算總量
    const bidTotalVolume = bids.reduce((sum, bid) => sum + bid.volume, 0);
    const askTotalVolume = asks.reduce((sum, ask) => sum + ask.volume, 0);

    document.getElementById('bidTotalVolume').textContent = bidTotalVolume;
    document.getElementById('askTotalVolume').textContent = askTotalVolume;

    // 建立表格
    tbody.innerHTML = '';

    for (let i = 0; i < 5; i++) {
        const row = document.createElement('tr');

        // 買進
        const bidCell = document.createElement('td');
        if (i < bids.length) {
            bidCell.textContent = bids[i].volume;
            bidCell.className = 'bid-cell';
        } else {
            bidCell.textContent = '--';
        }
        row.appendChild(bidCell);

        // 價格（賣出價優先）
        const priceCell = document.createElement('td');
        if (i < asks.length) {
            priceCell.textContent = asks[i].price.toFixed(2);
        } else if (i < bids.length) {
            priceCell.textContent = bids[i].price.toFixed(2);
        } else {
            priceCell.textContent = '--';
        }
        row.appendChild(priceCell);

        // 賣出
        const askCell = document.createElement('td');
        if (i < asks.length) {
            askCell.textContent = asks[i].volume;
            askCell.className = 'ask-cell';
        } else {
            askCell.textContent = '--';
        }
        row.appendChild(askCell);

        tbody.appendChild(row);
    }
}

// 更新成交明細
function updateTrades(trades) {
    const tbody = document.getElementById('tradesTableBody');

    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="no-data">暫無資料</td></tr>';
        allTradesData = [];
        return;
    }

    // 保存完整的交易資料（反向排序，最新的在前）
    allTradesData = [...trades];

    tbody.innerHTML = '';

    trades.forEach((trade, index) => {
        const row = document.createElement('tr');
        row.setAttribute('data-trade-index', index);
        row.setAttribute('data-timestamp', trade.time);

        // 添加點擊事件
        row.addEventListener('click', () => {
            highlightChartPoint(index);
        });

        // 時間
        const timeCell = document.createElement('td');
        timeCell.textContent = formatTime(trade.time);
        row.appendChild(timeCell);

        // 價格
        const priceCell = document.createElement('td');
        priceCell.textContent = trade.price.toFixed(2);
        priceCell.className = 'trade-price';
        row.appendChild(priceCell);

        // 單量
        const volumeCell = document.createElement('td');
        volumeCell.textContent = trade.volume;
        row.appendChild(volumeCell);

        // 內外盤
        const innerOuterCell = document.createElement('td');
        innerOuterCell.textContent = trade.inner_outer || '–';
        // 根據內外盤設定樣式
        if (trade.inner_outer === '內盤') {
            innerOuterCell.className = 'bid-cell';
        } else if (trade.inner_outer === '外盤') {
            innerOuterCell.className = 'ask-cell';
        }
        row.appendChild(innerOuterCell);

        tbody.appendChild(row);
    });
}

// 根據圖表索引滾動到對應的成交明細
function scrollToTradeByIndex(chartIndex) {
    if (!allTradesData || allTradesData.length === 0) {
        return;
    }

    // 圖表的數據是按時間正序排列的
    // 成交明細是按時間倒序排列的（最新的在前）
    // 所以需要轉換索引
    const tradesCount = allTradesData.length;
    const tradeIndex = tradesCount - 1 - chartIndex;

    if (tradeIndex < 0 || tradeIndex >= tradesCount) {
        return;
    }

    const tbody = document.getElementById('tradesTableBody');
    const targetRow = tbody.querySelector(`tr[data-trade-index="${tradeIndex}"]`);

    if (targetRow) {
        // 移除之前的高亮
        const previousHighlight = tbody.querySelector('.highlight-row');
        if (previousHighlight) {
            previousHighlight.classList.remove('highlight-row');
        }

        // 添加高亮
        targetRow.classList.add('highlight-row');

        // 禁用滾動監聽（避免觸發滾動事件）
        isUserScrolling = false;

        // 滾動到該行
        const container = document.querySelector('.trades-container');
        const containerRect = container.getBoundingClientRect();
        const rowRect = targetRow.getBoundingClientRect();

        if (rowRect.top < containerRect.top || rowRect.bottom > containerRect.bottom) {
            targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        // 更新五檔顯示
        updateDepthByTradeIndex(tradeIndex);

        // 3秒後移除高亮
        setTimeout(() => {
            targetRow.classList.remove('highlight-row');
        }, 3000);

        // 重新啟用滾動監聽
        setTimeout(() => {
            isUserScrolling = true;
        }, 1000);
    }
}

// 點擊成交明細時高亮圖表上的點
function highlightChartPoint(tradeIndex, showRedDot = true) {
    if (!priceChart || !allTradesData || allTradesData.length === 0) {
        return;
    }

    // 轉換索引（成交明細是倒序，圖表是正序）
    const tradesCount = allTradesData.length;
    const chartIndex = tradesCount - 1 - tradeIndex;

    if (chartIndex < 0 || chartIndex >= tradesCount) {
        return;
    }

    if (!showRedDot) {
        // 只更新五檔，不顯示紅點
        return;
    }

    // 創建臨時高亮點的數據集
    const highlightData = new Array(tradesCount).fill(null);
    highlightData[chartIndex] = priceChart.data.datasets[0].data[chartIndex];

    // 檢查是否已有高亮數據集
    let highlightDataset = priceChart.data.datasets.find(ds => ds.label === '選中點');

    if (highlightDataset) {
        highlightDataset.data = highlightData;
    } else {
        priceChart.data.datasets.push({
            label: '選中點',
            data: highlightData,
            borderColor: '#ff0000',
            backgroundColor: '#ff0000',
            pointRadius: 8,
            pointHoverRadius: 8,
            showLine: false
        });
    }

    priceChart.update();

    // 3秒後移除高亮
    setTimeout(() => {
        const index = priceChart.data.datasets.findIndex(ds => ds.label === '選中點');
        if (index > -1) {
            priceChart.data.datasets.splice(index, 1);
            priceChart.update();
        }
    }, 3000);
}

// 載入五檔歷史資料（用於互動）
async function loadDepthHistoryData(date, stock) {
    try {
        const response = await axios.get(`/api/depth_history/${date}/${stock}`);
        allDepthHistory = response.data || [];
        console.log(`載入了 ${allDepthHistory.length} 筆五檔歷史資料`);

        // 建立統一時間軸
        buildUnifiedTimeline();
    } catch (error) {
        console.error('載入五檔歷史失敗:', error);
        allDepthHistory = [];
    }
}

// 建立統一時間軸（以五檔為主，因為五檔變化更頻繁）
function buildUnifiedTimeline() {
    // 時間軸就是五檔的所有時間點（五檔變化驅動時間前進）
    allTimeline = allDepthHistory.map(depth => depth.timestamp);

    console.log(`建立統一時間軸（以五檔為主）：共 ${allTimeline.length} 個時間點`);
    console.log(`  - Depth 時間點: ${allDepthHistory.length}`);
    console.log(`  - Trade 時間點: ${allTradesData.length}`);
    console.log(`  - 五檔變化頻率 ≈ ${(allDepthHistory.length / allTradesData.length).toFixed(1)}x 成交頻率`);
}

// 重新整理資料
function refreshData() {
    if (currentDate && currentStock) {
        loadStockData(currentDate, currentStock);
    } else {
        loadDates();
    }
}

// 格式化日期
function formatDate(dateStr) {
    if (dateStr.length !== 8) {
        return dateStr;
    }
    return `${dateStr.substr(0, 4)}-${dateStr.substr(4, 2)}-${dateStr.substr(6, 2)}`;
}

// 成交明細滾動事件處理
function onTradesScroll() {
    // 清除之前的定時器
    if (scrollTimeout) {
        clearTimeout(scrollTimeout);
    }

    // 設定新的定時器，延遲執行（減少頻繁觸發）
    scrollTimeout = setTimeout(() => {
        if (!isUserScrolling) {
            isUserScrolling = true;
            return;
        }

        updateDepthByVisibleTrade();
    }, 100);
}

// 根據當前可見的成交明細更新五檔
function updateDepthByVisibleTrade() {
    const container = document.querySelector('.trades-container');
    const tbody = document.getElementById('tradesTableBody');

    if (!container || !tbody || allTradesData.length === 0) {
        return;
    }

    // 獲取容器的中心位置
    const containerRect = container.getBoundingClientRect();
    const centerY = containerRect.top + containerRect.height / 2;

    // 找出最接近中心的交易行
    const rows = tbody.querySelectorAll('tr[data-trade-index]');
    let closestRow = null;
    let minDistance = Infinity;

    rows.forEach(row => {
        const rowRect = row.getBoundingClientRect();
        const rowCenterY = rowRect.top + rowRect.height / 2;
        const distance = Math.abs(rowCenterY - centerY);

        if (distance < minDistance) {
            minDistance = distance;
            closestRow = row;
        }
    });

    if (closestRow) {
        const tradeIndex = parseInt(closestRow.getAttribute('data-trade-index'));
        updateDepthByTradeIndex(tradeIndex);

        // 更新圖表高亮（可選）
        highlightChartPoint(tradeIndex, false); // 傳入 false 表示不顯示紅點
    }
}

// 根據交易索引更新五檔
function updateDepthByTradeIndex(tradeIndex) {
    if (tradeIndex < 0 || tradeIndex >= allTradesData.length || allDepthHistory.length === 0) {
        return;
    }

    const trade = allTradesData[tradeIndex];
    const timestamp = trade.time;

    // 找到最接近的五檔資料
    const closestDepth = findClosestDepthByTimestamp(timestamp);

    if (closestDepth) {
        // 更新五檔顯示
        updateDepthDisplay(closestDepth);
    }
}

// 根據時間戳找到五檔資料（向前查找：只查找時間點之前或同時的最後一次五檔更新）
function findClosestDepthByTimestamp(targetTimestamp) {
    if (!allDepthHistory || allDepthHistory.length === 0) {
        return null;
    }

    const targetTime = new Date(targetTimestamp).getTime();
    let latestDepth = null;

    // 向前查找：找到時間點之前或同時的最後一次五檔更新
    // allDepthHistory 已經按時間正序排序（09:00 -> 13:30）
    for (const depth of allDepthHistory) {
        const depthTime = new Date(depth.timestamp).getTime();

        // 如果五檔時間晚於目標時間，停止查找
        if (depthTime > targetTime) {
            break;
        }

        // 保存這個五檔（因為它的時間 <= 目標時間）
        latestDepth = depth;
    }

    return latestDepth;
}

// 更新五檔顯示（支援歷史資料）
function updateDepthDisplay(depthData) {
    const tbody = document.getElementById('depthTableBody');

    if (!depthData || (!depthData.bids.length && !depthData.asks.length)) {
        return; // 保持當前顯示
    }

    // 更新時間顯示
    const timestampElem = document.getElementById('depthTimestamp');
    if (timestampElem && depthData.timestamp) {
        timestampElem.textContent = `@ ${formatTime(depthData.timestamp)}`;
    }

    // 確保有五檔
    const bids = depthData.bids.slice(0, 5);
    const asks = depthData.asks.slice(0, 5);

    // 計算總量
    const bidTotalVolume = bids.reduce((sum, bid) => sum + bid.volume, 0);
    const askTotalVolume = asks.reduce((sum, ask) => sum + ask.volume, 0);

    document.getElementById('bidTotalVolume').textContent = bidTotalVolume;
    document.getElementById('askTotalVolume').textContent = askTotalVolume;

    // 建立表格
    tbody.innerHTML = '';

    for (let i = 0; i < 5; i++) {
        const row = document.createElement('tr');

        // 買進
        const bidCell = document.createElement('td');
        if (i < bids.length) {
            bidCell.textContent = bids[i].volume;
            bidCell.className = 'bid-cell';
        } else {
            bidCell.textContent = '--';
        }
        row.appendChild(bidCell);

        // 價格（賣出價優先）
        const priceCell = document.createElement('td');
        if (i < asks.length) {
            priceCell.textContent = asks[i].price.toFixed(2);
        } else if (i < bids.length) {
            priceCell.textContent = bids[i].price.toFixed(2);
        } else {
            priceCell.textContent = '--';
        }
        row.appendChild(priceCell);

        // 賣出
        const askCell = document.createElement('td');
        if (i < asks.length) {
            askCell.textContent = asks[i].volume;
            askCell.className = 'ask-cell';
        } else {
            askCell.textContent = '--';
        }
        row.appendChild(askCell);

        tbody.appendChild(row);
    }
}

// 時間軸滑桿變化事件
function onTimelineChange(event) {
    const value = parseInt(event.target.value);
    const maxIndex = allTimeline.length - 1;

    if (maxIndex < 0) return;

    // 計算時間軸索引
    const timelineIndex = Math.round((value / 100) * maxIndex);
    currentTimelineIndex = timelineIndex;

    // 停止播放
    if (isPlaying) {
        togglePlayback();
    }

    // 更新顯示
    updateByTimelineIndex(timelineIndex);
}

// 根據時間軸索引更新所有顯示（時間軸以五檔為主）
function updateByTimelineIndex(timelineIndex) {
    if (timelineIndex < 0 || timelineIndex >= allTimeline.length) {
        return;
    }

    // 時間軸索引 = 五檔索引（因為時間軸就是五檔的時間點）
    const depthIndex = timelineIndex;
    const currentDepth = allDepthHistory[depthIndex];
    const currentTime = currentDepth.timestamp;

    // 更新時間標籤
    const timelineLabel = document.getElementById('timelineLabel');
    if (timelineLabel) {
        timelineLabel.textContent = formatTime(currentTime);
    }

    // 禁用自動滾動監聽
    isUserScrolling = false;

    // 1. 更新五檔顯示（直接顯示當前五檔）
    updateDepthDisplay(currentDepth);

    // 2. 更新成交明細（顯示所有時間 <= currentTime 的成交）
    updateTradesUpToTime(currentTime);

    // 3. 自動調整圖表窗口以顯示當前時間點
    // 找到對應的圖表索引（在 allChartData 中）
    const chartIndex = findChartIndexByTime(currentTime);
    if (chartIndex >= 0) {
        // 找到對應的 Trade 索引（用於滾動控制）
        const tradeIndex = findTradeIndexByTime(currentTime);
        if (tradeIndex >= 0) {
            autoScrollChartToCurrentTime(tradeIndex);
        }
        // 更新圖表標記和均價
        updateCurrentPositionMarker(chartIndex);
        updateAvgPrice(chartIndex);
    }

    // 重新啟用滾動監聽
    setTimeout(() => {
        isUserScrolling = true;
    }, 1000);
}

// 根據時間找到對應的成交索引（用於圖表定位）
function findTradeIndexByTime(targetTime) {
    const targetTimestamp = new Date(targetTime).getTime();

    // allTradesData 是倒序的（最新的在前），需要找到最接近且不超過 targetTime 的成交
    for (let i = allTradesData.length - 1; i >= 0; i--) {
        const tradeTime = new Date(allTradesData[i].time).getTime();
        if (tradeTime <= targetTimestamp) {
            return i; // 返回倒序索引
        }
    }

    return allTradesData.length - 1; // 如果沒找到，返回最早的成交
}

// 根據時間找到對應的圖表索引（在 allChartData 中）
function findChartIndexByTime(targetTime) {
    if (!allChartData || !allChartData.timestamps || allChartData.timestamps.length === 0) {
        return -1;
    }

    const targetTimestamp = new Date(targetTime).getTime();

    // allChartData.timestamps 是正序的（09:00 -> 13:30），找到最接近且不超過 targetTime 的點
    let closestIndex = -1;
    for (let i = 0; i < allChartData.timestamps.length; i++) {
        const chartTime = new Date(allChartData.timestamps[i]).getTime();
        if (chartTime <= targetTimestamp) {
            closestIndex = i;
        } else {
            break; // 已經超過目標時間，停止搜索
        }
    }

    return closestIndex;
}

// 更新成交明細（顯示所有時間 <= currentTime 的成交）
function updateTradesUpToTime(currentTime) {
    const tbody = document.getElementById('tradesTableBody');
    const currentTimestamp = new Date(currentTime).getTime();

    // 清空現有的成交明細
    tbody.innerHTML = '';

    // 過濾出時間 <= currentTime 的成交（倒序顯示：最新的在前）
    const visibleTrades = allTradesData.filter(trade => {
        const tradeTime = new Date(trade.time).getTime();
        return tradeTime <= currentTimestamp;
    });

    if (visibleTrades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="no-data">暫無成交</td></tr>';
        return;
    }

    // 顯示成交明細（已經是倒序）
    visibleTrades.forEach((trade, index) => {
        const row = document.createElement('tr');
        row.setAttribute('data-trade-index', index);
        row.setAttribute('data-timestamp', trade.time);

        // 時間
        const timeCell = document.createElement('td');
        timeCell.textContent = formatTime(trade.time);
        row.appendChild(timeCell);

        // 價格
        const priceCell = document.createElement('td');
        priceCell.textContent = trade.price.toFixed(2);
        priceCell.className = 'trade-price';
        row.appendChild(priceCell);

        // 單量
        const volumeCell = document.createElement('td');
        volumeCell.textContent = trade.volume;
        row.appendChild(volumeCell);

        // 內外盤
        const innerOuterCell = document.createElement('td');
        innerOuterCell.textContent = trade.inner_outer || '–';
        // 根據內外盤設定樣式
        if (trade.inner_outer === '內盤') {
            innerOuterCell.className = 'bid-cell';
        } else if (trade.inner_outer === '外盤') {
            innerOuterCell.className = 'ask-cell';
        }
        row.appendChild(innerOuterCell);

        tbody.appendChild(row);
    });

    // 自動滾動到最新的成交（最上面）
    tbody.scrollTop = 0;
}

// 更新圖表上的當前位置紅點
function updateCurrentPositionMarker(chartIndex) {
    if (!allChartData || !allChartData.timestamps || chartIndex < 0 || chartIndex >= allChartData.timestamps.length) {
        // 清除紅點
        if (priceChart && priceChart.data.datasets.length > 2) {
            priceChart.data.datasets[2].data = [];
            priceChart.update('none'); // 使用 'none' 模式避免動畫
        }
        return;
    }

    const timestamp = allChartData.timestamps[chartIndex];
    const price = allChartData.prices[chartIndex];

    if (price !== null && price !== undefined) {
        // 更新紅點位置
        if (priceChart && priceChart.data.datasets.length > 2) {
            priceChart.data.datasets[2].data = [{ x: timestamp, y: price }];
            priceChart.update('none'); // 使用 'none' 模式避免動畫
        }
    }
}

// 更新均價顯示（根據當前回放位置）
function updateAvgPrice(chartIndex) {
    if (!allChartData || !allChartData.vwap || chartIndex < 0 || chartIndex >= allChartData.vwap.length) {
        return;
    }

    const avgPrice = allChartData.vwap[chartIndex];
    const avgPriceElem = document.getElementById('avgPrice');

    if (avgPriceElem && avgPrice !== null && avgPrice !== undefined) {
        avgPriceElem.textContent = avgPrice.toFixed(2);
    }
}

// 自動調整圖表窗口以顯示當前時間點
function autoScrollChartToCurrentTime(tradeIndex) {
    if (!allChartData || allChartData.timestamps.length === 0) {
        return;
    }

    // 轉換索引（成交明細是倒序，圖表是正序）
    const totalTrades = allTradesData.length;
    const chartIndex = totalTrades - 1 - tradeIndex;

    if (chartIndex < 0 || chartIndex >= allChartData.timestamps.length) {
        return;
    }

    // 計算當前時間點在完整資料中的百分比位置
    const currentPercentage = (chartIndex / (allChartData.timestamps.length - 1)) * 100;

    // 計算當前窗口的起始和結束百分比
    const windowEnd = chartWindowStart + chartWindowSize;

    // 如果當前時間點不在可見範圍內，調整窗口位置
    // 讓當前時間點保持在窗口的中間位置
    if (currentPercentage < chartWindowStart || currentPercentage > windowEnd) {
        // 計算新的窗口起始位置（讓當前點在窗口中間）
        let newStart = currentPercentage - (chartWindowSize / 2);

        // 確保不超出範圍
        newStart = Math.max(0, newStart);
        newStart = Math.min(newStart, 100 - chartWindowSize);

        chartWindowStart = newStart;

        // 更新圖表顯示
        updateChartDisplay();

        // 更新圖表時間軸滑桿位置
        const chartTimelineSlider = document.getElementById('chartTimelineSlider');
        if (chartTimelineSlider) {
            chartTimelineSlider.value = chartWindowStart;
        }

        // 更新時間標籤
        updateChartTimelineLabels();
    }
}

// 播放/暫停切換
function togglePlayback() {
    isPlaying = !isPlaying;
    const playPauseBtn = document.getElementById('playPauseBtn');

    if (isPlaying) {
        playPauseBtn.textContent = '⏸ 暫停';
        startPlayback();
    } else {
        playPauseBtn.textContent = '▶️ 播放';
        stopPlayback();
    }
}

// 開始播放
function startPlayback() {
    const speedSelect = document.getElementById('playbackSpeed');
    const speed = parseFloat(speedSelect.value);
    const interval = 1000 / speed; // 基礎速度為1秒1筆

    playbackInterval = setInterval(() => {
        // 時間軸是正序（09:00 -> 13:30），播放時 index 遞增
        currentTimelineIndex++;

        if (currentTimelineIndex >= allTimeline.length) {
            // 播放完畢（到達 13:30），停止
            currentTimelineIndex = allTimeline.length - 1;
            togglePlayback();
            return;
        }

        // 更新滑桿位置
        const timelineSlider = document.getElementById('timelineSlider');
        const percentage = (currentTimelineIndex / (allTimeline.length - 1)) * 100;
        timelineSlider.value = percentage;

        // 更新顯示
        updateByTimelineIndex(currentTimelineIndex);
    }, interval);
}

// 停止播放
function stopPlayback() {
    if (playbackInterval) {
        clearInterval(playbackInterval);
        playbackInterval = null;
    }
}

// 初始化時間軸控制
function initializeTimeline() {
    if (allTimeline.length === 0 || allDepthHistory.length === 0) {
        // 隱藏時間軸控制
        const timelineControl = document.getElementById('timelineControl');
        const playPauseBtn = document.getElementById('playPauseBtn');
        if (timelineControl) timelineControl.style.display = 'none';
        if (playPauseBtn) playPauseBtn.style.display = 'none';
        return;
    }

    // 顯示時間軸控制
    const timelineControl = document.getElementById('timelineControl');
    const playPauseBtn = document.getElementById('playPauseBtn');
    if (timelineControl) timelineControl.style.display = 'flex';
    if (playPauseBtn) {
        playPauseBtn.style.display = 'inline-block';
        playPauseBtn.textContent = '▶️ 播放';  // 設置初始文字
    }

    // 重置播放狀態
    isPlaying = false;
    if (playbackInterval) {
        clearInterval(playbackInterval);
        playbackInterval = null;
    }

    // 從 09:00 開始（時間軸是正序的，從第一筆五檔開始）
    let startIndex = 0;
    currentTimelineIndex = startIndex;

    // 設置滑桿
    const timelineSlider = document.getElementById('timelineSlider');
    if (timelineSlider) {
        timelineSlider.max = 100;
        timelineSlider.value = 0; // 從 0% 開始（09:00）
    }

    // 設置初始時間標籤並更新顯示
    const timelineLabel = document.getElementById('timelineLabel');
    if (timelineLabel && allTimeline.length > 0) {
        timelineLabel.textContent = formatTime(allTimeline[startIndex]);
    }

    // 更新到 09:00 的位置（第一筆五檔）
    // 使用 setTimeout 確保 DOM 已經完全渲染
    setTimeout(() => {
        updateByTimelineIndex(startIndex);
    }, 100);
}

// 初始化圖表時間軸控制
function initializeChartTimeline() {
    const chartTimelineControl = document.getElementById('chartTimelineControl');

    if (!allChartData || allChartData.timestamps.length === 0) {
        if (chartTimelineControl) {
            chartTimelineControl.style.display = 'none';
        }
        return;
    }

    // 顯示圖表時間軸控制
    if (chartTimelineControl) {
        chartTimelineControl.style.display = 'flex';
    }

    // 重置滑桿
    const chartTimelineSlider = document.getElementById('chartTimelineSlider');
    if (chartTimelineSlider) {
        chartTimelineSlider.value = 0;
        chartTimelineSlider.max = 100;
    }

    // 更新時間標籤
    updateChartTimelineLabels();
}

// 圖表時間軸滑桿變化事件
function onChartTimelineChange(event) {
    const value = parseInt(event.target.value);

    // 計算新的窗口起始位置
    const maxStart = 100 - chartWindowSize;
    chartWindowStart = Math.min(value, maxStart);

    // 更新圖表顯示
    updateChartDisplay();

    // 更新時間標籤
    updateChartTimelineLabels();
}

// 放大圖表
function zoomInChart() {
    // 減少窗口大小（最小 10%）
    chartWindowSize = Math.max(10, chartWindowSize - 10);

    // 調整起始位置，確保不超出範圍
    const maxStart = 100 - chartWindowSize;
    chartWindowStart = Math.min(chartWindowStart, maxStart);

    // 更新滑桿最大值
    const chartTimelineSlider = document.getElementById('chartTimelineSlider');
    if (chartTimelineSlider) {
        chartTimelineSlider.max = maxStart;
        chartTimelineSlider.value = chartWindowStart;
    }

    // 更新顯示
    updateChartDisplay();
    updateChartTimelineLabels();
}

// 縮小圖表
function zoomOutChart() {
    // 增加窗口大小（最大 100%）
    chartWindowSize = Math.min(100, chartWindowSize + 10);

    // 調整起始位置，確保不超出範圍
    const maxStart = 100 - chartWindowSize;
    chartWindowStart = Math.min(chartWindowStart, maxStart);

    // 更新滑桿最大值
    const chartTimelineSlider = document.getElementById('chartTimelineSlider');
    if (chartTimelineSlider) {
        chartTimelineSlider.max = maxStart;
        chartTimelineSlider.value = chartWindowStart;
    }

    // 更新顯示
    updateChartDisplay();
    updateChartTimelineLabels();
}

// 重置圖表縮放
function resetChartZoom() {
    chartWindowSize = 100;
    chartWindowStart = 0;

    // 重置滑桿
    const chartTimelineSlider = document.getElementById('chartTimelineSlider');
    if (chartTimelineSlider) {
        chartTimelineSlider.value = 0;
        chartTimelineSlider.max = 100;
    }

    // 更新顯示
    updateChartDisplay();
    updateChartTimelineLabels();
}

// 更新圖表時間軸標籤
function updateChartTimelineLabels() {
    if (!allChartData || allChartData.timestamps.length === 0) {
        return;
    }

    const totalPoints = allChartData.timestamps.length;
    const startIndex = Math.floor((chartWindowStart / 100) * totalPoints);
    const endIndex = Math.min(
        Math.ceil(((chartWindowStart + chartWindowSize) / 100) * totalPoints) - 1,
        totalPoints - 1
    );

    const startTime = allChartData.timestamps[startIndex];
    const endTime = allChartData.timestamps[endIndex];

    // 更新標籤（只顯示 HH:MM 格式）
    const chartStartTimeElem = document.getElementById('chartStartTime');
    const chartEndTimeElem = document.getElementById('chartEndTime');

    if (chartStartTimeElem) {
        chartStartTimeElem.textContent = formatTimeShort(startTime);
    }

    if (chartEndTimeElem) {
        chartEndTimeElem.textContent = formatTimeShort(endTime);
    }
}

// 格式化時間（短格式 HH:MM）
function formatTimeShort(timestamp) {
    if (!timestamp) {
        return '--:--';
    }

    try {
        const date = new Date(timestamp);
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    } catch {
        return '--:--';
    }
}

// 格式化時間
function formatTime(timestamp) {
    if (!timestamp) {
        return '--';
    }

    try {
        const date = new Date(timestamp);
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const seconds = date.getSeconds().toString().padStart(2, '0');
        const ms = date.getMilliseconds().toString().padStart(3, '0'); // 顯示三位小數秒（毫秒）
        return `${hours}:${minutes}:${seconds}.${ms}`;
    } catch {
        // 備用格式處理
        if (typeof timestamp === 'string' && timestamp.length >= 23) {
            return timestamp.substr(11, 12); // HH:MM:SS.mmm
        }
        return timestamp;
    }
}
