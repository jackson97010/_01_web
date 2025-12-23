import React, { useEffect, useMemo, useState, useRef } from 'react';
import { prepareReplay, getStateAtIndex } from './utils/replay';
import { ReplayRow, DepthRow, TradeRow } from './types';
import PriceChart from './components/PriceChart';
import { parseStreamLine } from './utils/streamParser';  // 新增串流解析器

const DEFAULT_PATH =
  'C:\\\\Users\\\\User\\\\Documents\\\\HFT\\\\_replay_system\\\\3060_1219.json';

function renderButterflyWithDiff(
  currDepth: DepthRow | null,
  prevDepth: DepthRow | null,
  totalIn: number,
  totalOut: number
): string {
  console.log('renderButterflyWithDiff called with:', {
    hasDepth: !!currDepth,
    depthType: currDepth?.Type,
    bid1: currDepth?.Bid1_Price,
    ask1: currDepth?.Ask1_Price
  });

  if (!currDepth) {
    return "<div class='ob-container' style='padding:20px;text-align:center'>等待五檔資料...</div>";
  }

  const total = (totalIn || 0) + (totalOut || 0);
  const inPct = total > 0 ? (totalIn / total) * 100 : 50;
  const outPct = total > 0 ? (totalOut / total) * 100 : 50;

  const vols: number[] = [];
  for (let i = 1; i <= 5; i += 1) {
    vols.push(Number(currDepth[`Bid${i}_Volume`] || 0));
    vols.push(Number(currDepth[`Ask${i}_Volume`] || 0));
  }
  const maxVol = Math.max(1, Math.max(...vols));

  let rowsHtml = '';
  for (let i = 1; i <= 5; i += 1) {
    const bp = Number(currDepth[`Bid${i}_Price`] || 0);
    const bv = Number(currDepth[`Bid${i}_Volume`] || 0);
    const ap = Number(currDepth[`Ask${i}_Price`] || 0);
    const av = Number(currDepth[`Ask${i}_Volume`] || 0);

    const prevBp = Number(prevDepth?.[`Bid${i}_Price`] || 0);
    const prevBv = Number(prevDepth?.[`Bid${i}_Volume`] || 0);
    const prevAp = Number(prevDepth?.[`Ask${i}_Price`] || 0);
    const prevAv = Number(prevDepth?.[`Ask${i}_Volume`] || 0);

    let bidDiff = '';
    if (bp > 0 && bp === prevBp && bv !== prevBv) {
      const diff = bv - prevBv;
      const color = diff > 0 ? 'var(--up)' : 'var(--down)';
      const sign = diff > 0 ? '+' : '';
      bidDiff = `<span class='diff-txt' style='color:${color}'>(${sign}${diff})</span>`;
    }

    let askDiff = '';
    if (ap > 0 && ap === prevAp && av !== prevAv) {
      const diff = av - prevAv;
      const color = diff > 0 ? 'var(--up)' : 'var(--down)';
      const sign = diff > 0 ? '+' : '';
      askDiff = `<span class='diff-txt' style='color:${color}'>(${sign}${diff})</span>`;
    }

    const bvW = bv > 0 ? Math.min(96, (bv / maxVol) * 96) : 0;
    const avW = av > 0 ? Math.min(96, (av / maxVol) * 96) : 0;

    const bpTxt = bp > 0 ? bp.toFixed(2) : '-';
    const bvTxt = bv > 0 ? `${Math.trunc(bv)}` : '-';
    const apTxt = ap > 0 ? ap.toFixed(2) : '-';
    const avTxt = av > 0 ? `${Math.trunc(av)}` : '-';

    rowsHtml += `
      <tr>
        <td class="bid-vol">
          <div class="vol-bar-bg bid-bar" style="width:${bvW.toFixed(2)}%;"></div>
          <div class="vol-text" style="justify-content:flex-end;">${bvTxt}${bidDiff}</div>
        </td>
        <td class="bid-price">${bpTxt}</td>
        <td class="ask-price">${apTxt}</td>
        <td class="ask-vol">
          <div class="vol-bar-bg ask-bar" style="width:${avW.toFixed(2)}%;"></div>
          <div class="vol-text" style="justify-content:flex-start;">${avTxt}${askDiff}</div>
        </td>
      </tr>
    `;
  }

  return `
    <div class="ob-container">
      <div class="io-row">
        <span style="color:var(--down)">內盤 ${totalIn.toLocaleString()}</span>
        <span style="color:var(--up)">外盤 ${totalOut.toLocaleString()}</span>
      </div>
      <div class="io-bar">
        <div style="width:${inPct.toFixed(2)}%; background:var(--down);"></div>
        <div style="width:${outPct.toFixed(2)}%; background:var(--up);"></div>
      </div>
      <table class="ob-table">
        <thead>
          <tr><th>委買量</th><th>買價</th><th>賣價</th><th>委賣量</th></tr>
        </thead>
        <tbody>${rowsHtml}</tbody>
      </table>
    </div>
  `;
}

function formatMicro(dt?: string | Date) {
  if (!dt) return '--';

  // 如果是字串格式 (e.g., "2025-12-19 09:04:49.150000")
  if (typeof dt === 'string') {
    // 提取時間部分 "09:04:49.150000"
    const timePart = dt.split(' ')[1];
    if (timePart) {
      return timePart;
    }
  }

  // 如果是 Date 物件，嘗試保留原始精度
  if (dt instanceof Date) {
    const pad = (n: number, len = 2) => n.toString().padStart(len, '0');
    const millis = dt.getMilliseconds();
    // 注意：Date 物件只能精確到毫秒，無法保留微秒
    return `${pad(dt.getHours())}:${pad(dt.getMinutes())}:${pad(dt.getSeconds())}.${pad(millis, 3)}000`;
  }

  return '--';
}

const App: React.FC = () => {
  const [filePath, setFilePath] = useState(DEFAULT_PATH);
  const [rawRows, setRawRows] = useState<any[]>([]);
  const [idx, setIdx] = useState(0);
  const [running, setRunning] = useState(false);
  const [totalIn, setTotalIn] = useState(0);
  const [totalOut, setTotalOut] = useState(0);
  const [jumpTime, setJumpTime] = useState('09:00:00.000000');
  const [status, setStatus] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // 即時模式相關狀態
  const [liveMode, setLiveMode] = useState(false);
  const [liveConnected, setLiveConnected] = useState(false);
  const [liveBuffer, setLiveBuffer] = useState<any[]>([]);
  const [selectedStock, setSelectedStock] = useState<string>('4939'); // 預設選擇第一支股票
  const [availableStocks, setAvailableStocks] = useState<string[]>([]);

  const replayData = useMemo<ReplayRow[]>(() => {
    if (!rawRows.length) return [];
    return prepareReplay(rawRows);
  }, [rawRows]);

  // 提取所有成交數據用於圖表
  const allTrades = useMemo<TradeRow[]>(() => {
    return replayData.filter(row => row.Type === 'Trade') as TradeRow[];
  }, [replayData]);

  const currentRow = replayData[idx];
  const { lastDepth, prevDepth, lastTrade } = useMemo(
    () => getStateAtIndex(replayData, idx),
    [replayData, idx]
  );

  // 調試：輸出當前狀態
  useEffect(() => {
    if (lastDepth) {
      console.log('Current Depth:', {
        Bid1_Price: lastDepth.Bid1_Price,
        Bid1_Volume: lastDepth.Bid1_Volume,
        Ask1_Price: lastDepth.Ask1_Price,
        Ask1_Volume: lastDepth.Ask1_Volume,
        Type: lastDepth.Type,
        Timestamp: lastDepth.Timestamp,
        Datetime: lastDepth.Datetime
      });

      // 檢查所有五檔數據
      for (let i = 1; i <= 5; i++) {
        const bidPrice = lastDepth[`Bid${i}_Price`];
        const askPrice = lastDepth[`Ask${i}_Price`];
        if (bidPrice === undefined || bidPrice === null || askPrice === undefined || askPrice === null) {
          console.warn(`Missing depth level ${i}: Bid=${bidPrice}, Ask=${askPrice}`);
        }
      }
    } else {
      console.log('No depth data at index:', idx);
    }
  }, [idx, lastDepth]);

  useEffect(() => {
    if (!running || replayData.length === 0) return undefined;
    const h = setInterval(() => {
      setIdx((i) => {
        if (i + 1 >= replayData.length) {
          setRunning(false);
          return i;
        }
        return i + 1;
      });
    }, 20); // 從 50ms 減少到 20ms，播放更快
    return () => clearInterval(h);
  }, [running, replayData.length]);

  useEffect(() => {
    if (!running) return;
    const row = replayData[idx];
    if (row?.Type === 'Trade') {
      const vol = Number((row as TradeRow).Volume || 0);
      if (row.BS_Flag === 'In') setTotalIn((v) => v + vol);
      else if (row.BS_Flag === 'Out') setTotalOut((v) => v + vol);
    }
  }, [idx, running, replayData]);

  // 載入可用的股票列表
  useEffect(() => {
    const loadStocks = async () => {
      try {
        const stocks = await window.electronAPI.getAvailableStocks();
        setAvailableStocks(stocks);
      } catch (err) {
        console.error('Failed to load available stocks:', err);
      }
    };
    loadStocks();
  }, []);

  // 即時資料監聽
  useEffect(() => {
    if (!liveMode) return;

    const unsubscribe = window.electronAPI.onMarketDataUpdate((data: any) => {
      console.log('Received market data:', data);

      // 處理原始格式的串流資料
      if (typeof data === 'string') {
        const parsed = parseStreamLine(data);
        if (parsed) {
          console.log('Parsed stream data:', parsed);

          // 將解析後的資料加入緩衝區
          setLiveBuffer(prev => {
            const newBuffer = [...prev, parsed];
            // 限制緩衝區大小，保留最新的 10000 筆資料
            if (newBuffer.length > 10000) {
              return newBuffer.slice(-10000);
            }
            return newBuffer;
          });

          // 更新內外盤統計
          if (parsed.Type === 'Trade') {
            const trade = parsed as TradeRow;
            if (trade.BS_Flag === 'Out') {
              setTotalOut(prev => prev + (trade.Volume || 0));
            } else if (trade.BS_Flag === 'In') {
              setTotalIn(prev => prev + (trade.Volume || 0));
            }
          }
        }
      } else if (data.type === 'tick-batch' && data.data) {
        // 相容舊格式
        setLiveBuffer(prev => {
          const newBuffer = [...prev, ...data.data];
          if (newBuffer.length > 10000) {
            return newBuffer.slice(-10000);
          }
          return newBuffer;
        });

        data.data.forEach((tick: any) => {
          if (tick.tickType === 1) {
            setTotalOut(prev => prev + tick.volume);
          } else if (tick.tickType === 2) {
            setTotalIn(prev => prev + tick.volume);
          }
        });
      }
    });

    return () => {
      unsubscribe();
    };
  }, [liveMode]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        setRunning(false);
        setIdx((i) => Math.max(0, i - 1));
      } else if (e.key === 'ArrowRight') {
        setRunning(false);
        setIdx((i) => Math.min(replayData.length - 1, i + 1));
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [replayData.length]);

  const handlePick = async () => {
    const picked = await window.electronAPI.pickFile();
    if (picked) setFilePath(picked);
  };

  const handleLoad = async () => {
    try {
      setLoading(true);
      setError(null);
      setStatus('載入中...');
      console.log('Loading file:', filePath);
      const rows = await window.electronAPI.loadFile(filePath);
      console.log('Loaded rows:', rows.length);
      console.log('First 5 rows:', rows.slice(0, 5));

      // Check for Depth and Trade data
      const depthCount = rows.filter((r: any) => r?.Type === 'Depth').length;
      const tradeCount = rows.filter((r: any) => r?.Type === 'Trade').length;
      console.log(`Data contains: ${depthCount} Depth rows, ${tradeCount} Trade rows`);

      setRawRows(rows);
      setIdx(0);
      setRunning(false);
      setTotalIn(0);
      setTotalOut(0);
      setStatus(`已載入 ${rows.length} 筆資料 (Depth: ${depthCount}, Trade: ${tradeCount})`);
    } catch (err: any) {
      console.error('Load error:', err);
      setError(err?.message || '載入失敗');
      setStatus('');
    } finally {
      setLoading(false);
    }
  };

  const handleJump = () => {
    if (!replayData.length) return;

    // 將輸入的時間轉換為 Timestamp 格式 (HHMMSSffffff)
    const [hms = '00:00:00', microPart = '000000'] = jumpTime.split('.');
    const [h, m, s] = hms.split(':').map(Number);
    const targetTimestamp = h * 10000000000 + m * 100000000 + s * 1000000 + Number(microPart.padEnd(6, '0'));

    let newIdx = replayData.findIndex((row) => {
      return row.Timestamp >= targetTimestamp;
    });
    if (newIdx === -1) newIdx = replayData.length - 1;
    setIdx(newIdx);
    setRunning(false);
    setStatus(`跳至 ${hms}.${microPart}`);
  };

  const handlePrev = () => {
    setRunning(false);
    setIdx((i) => Math.max(0, i - 1));
  };

  const handleNext = () => {
    setRunning(false);
    setIdx((i) => Math.min(replayData.length - 1, i + 1));
  };

  // 處理即時模式切換
  const handleLiveModeToggle = async () => {
    if (liveMode) {
      // 停止即時模式
      try {
        const result = await window.electronAPI.stopLiveStream();
        if (result.success) {
          setLiveMode(false);
          setLiveConnected(false);
          setStatus('即時串流已停止');
        } else {
          setError(result.message || '停止失敗');
        }
      } catch (err: any) {
        setError(err.message || '停止失敗');
      }
    } else {
      // 啟動即時模式
      try {
        setStatus(`連接即時資料流中 (股票: ${selectedStock})...`);
        const result = await window.electronAPI.startLiveStream(selectedStock);
        if (result.success) {
          setLiveMode(true);
          setLiveConnected(true);
          setLiveBuffer([]);
          setTotalIn(0);
          setTotalOut(0);
          setRunning(false);
          setStatus(`即時串流已啟動 (股票: ${selectedStock})`);
        } else {
          setError(result.message || '連接失敗');
        }
      } catch (err: any) {
        setError(err.message || '連接失敗');
      }
    }
  };

  // 即時模式時顯示最新的資料
  const displayDepth = liveMode && liveBuffer.length > 0
    ? (() => {
        // 從緩衝區找出最新的 Depth 資料
        for (let i = liveBuffer.length - 1; i >= 0; i--) {
          if (liveBuffer[i]?.Type === 'Depth') {
            return liveBuffer[i] as DepthRow;
          }
        }
        return null;
      })()
    : lastDepth;

  const displayTrade = liveMode && liveBuffer.length > 0
    ? (() => {
        // 從緩衝區找出最新的 Trade 資料
        for (let i = liveBuffer.length - 1; i >= 0; i--) {
          if (liveBuffer[i]?.Type === 'Trade') {
            return liveBuffer[i] as TradeRow;
          }
        }
        return null;
      })()
    : lastTrade;

  const obHtml = renderButterflyWithDiff(displayDepth, prevDepth, totalIn, totalOut);
  const hasData = liveMode ? liveBuffer.length > 0 : replayData.length > 0;

  return (
    <div className="app-shell">
      <div className="panel controls">
        <div className="file-row">
          <input
            style={{ flex: 1 }}
            value={filePath}
            onChange={(e) => setFilePath(e.target.value)}
            placeholder="資料檔路徑 (JSON / Parquet)"
            disabled={liveMode}
          />
          <button className="secondary" onClick={handlePick} disabled={liveMode}>選檔</button>
          <button className="primary" onClick={handleLoad} disabled={loading || liveMode}>
            {loading ? '載入中...' : '重新載入'}
          </button>
          <select
            value={selectedStock}
            onChange={(e) => setSelectedStock(e.target.value)}
            disabled={liveMode}
            style={{ marginLeft: '10px', minWidth: '100px' }}
          >
            {availableStocks.map(stock => (
              <option key={stock} value={stock}>{stock}</option>
            ))}
          </select>
          <button
            className={liveMode ? 'danger' : 'success'}
            onClick={handleLiveModeToggle}
            style={{ marginLeft: '5px' }}
          >
            {liveMode ? '停止即時' : '即時串流'}
          </button>
        </div>
        {!liveMode && (
          <div className="jump-row">
            <input
              style={{ flex: 1 }}
              value={jumpTime}
              onChange={(e) => setJumpTime(e.target.value)}
              placeholder="HH:MM:SS.ffffff"
            />
            <button onClick={handleJump}>跳到時間</button>
            <span className="pill">Rows: {replayData.length}</span>
          </div>
        )}
        {liveMode && (
          <div className="jump-row">
            <span className="pill" style={{ background: liveConnected ? '#22c55e' : '#ef4444' }}>
              {liveConnected ? `即時連線中 (${selectedStock})` : '未連線'}
            </span>
            <span className="pill">緩衝區: {liveBuffer.length} 筆</span>
            <span className="pill">內盤: {totalIn.toLocaleString()}</span>
            <span className="pill">外盤: {totalOut.toLocaleString()}</span>
          </div>
        )}
        <div className="play-row">
          <button
            className="primary"
            onClick={() => setRunning((r) => !r)}
            disabled={!hasData || liveMode}
          >
            {running ? '暫停' : '播放'}
          </button>
          <button onClick={handlePrev} disabled={!hasData || liveMode}>上一筆</button>
          <button onClick={handleNext} disabled={!hasData || liveMode}>下一筆</button>
        </div>
      </div>

      <input
        className="timeline"
        type="range"
        min={0}
        max={Math.max(replayData.length - 1, 0)}
        value={idx}
        onChange={(e) => {
          setRunning(false);
          setIdx(Number(e.target.value));
        }}
        disabled={!hasData}
      />

      <div className="status">
        {status}
        {error && <span style={{ color: 'var(--up)', marginLeft: 10 }}>錯誤：{error}</span>}
        {hasData && (
          <span style={{ marginLeft: 12 }}>
            Index {idx + 1}/{replayData.length} | 類型: {currentRow?.Type || '--'}
          </span>
        )}
      </div>

      <div className="grid">
        <div className="panel" dangerouslySetInnerHTML={{ __html: obHtml }} />

        <div className="right-panel">
          <div className="panel ticker-section">
            {displayTrade ? (
              <div className="ticker-card">
                <div className="timestamp-micro">
                  {liveMode
                    ? formatMicro(displayTrade.datetime)
                    : formatMicro(displayTrade.Datetime)}
                </div>
                <div
                  className="big-price"
                  style={{
                    color:
                      displayTrade.BS_Flag === 'Out'
                        ? 'var(--up)'
                        : displayTrade.BS_Flag === 'In'
                        ? 'var(--down)'
                        : '#ffffff'
                  }}
                >
                  {liveMode ? (displayTrade.price ?? '--') : (displayTrade.Price ?? '--')}
                </div>
                <div className="ticker-row">
                  <span>成交量: {Number(liveMode ? (displayTrade.volume || 0) : (displayTrade.Volume || 0))}</span>
                  <span
                    className="tag"
                    style={{
                      background:
                        displayTrade.BS_Flag === 'Out'
                          ? 'rgba(255,77,79,0.16)'
                          : displayTrade.BS_Flag === 'In'
                          ? 'rgba(0,200,83,0.16)'
                          : '#222',
                      color:
                        displayTrade.BS_Flag === 'Out'
                          ? 'var(--up)'
                          : displayTrade.BS_Flag === 'In'
                          ? 'var(--down)'
                          : '#ddd'
                    }}
                  >
                    {displayTrade.BS_Flag === 'Out' ? '外盤' : displayTrade.BS_Flag === 'In' ? '內盤' : '—'}
                  </span>
                </div>
                {!liveMode && (
                  <div className="ticker-row" style={{ fontSize: 14, marginTop: 8 }}>
                    <span>索引: {idx}</span>
                    <span>型別: {currentRow?.Type || '--'}</span>
                  </div>
                )}
                <div className="ticker-row" style={{ fontSize: 14, marginTop: 8 }}>
                  <span>內盤累計: {totalIn.toLocaleString()}</span>
                  <span>外盤累計: {totalOut.toLocaleString()}</span>
                </div>
              </div>
            ) : (
              <div className="ticker-card">等待成交資料...</div>
            )}
          </div>

          <div className="panel chart-section">
            <h3 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#aaa' }}>走勢圖</h3>
            {allTrades.length > 0 ? (
              <PriceChart trades={allTrades} currentTimestamp={currentRow?.Timestamp || 0} />
            ) : (
              <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                等待成交數據...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
