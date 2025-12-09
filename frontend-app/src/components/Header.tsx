import { useMemo } from 'react';
import { useStockStore } from '@/stores/stockStore';
import { RefreshCw } from 'lucide-react';

export default function Header() {
  const {
    dates,
    stocks,
    selectedDate,
    selectedStock,
    setSelectedDate,
    setSelectedStock,
    stockData,
    loading,
    currentTimeIndex,
  } = useStockStore();

  // 根據當前時間索引動態計算統計資料
  const stats = useMemo(() => {
    if (!stockData?.stats || !stockData?.chart || !stockData?.unifiedTimeline) {
      return stockData?.stats || null;
    }

    const currentTime = stockData.unifiedTimeline[currentTimeIndex];
    if (!currentTime) {
      return stockData.stats;
    }

    // 找到當前時間之前的所有交易資料
    const timestamps = stockData.chart.timestamps;
    const prices = stockData.chart.prices;
    const volumes = stockData.chart.volumes;
    const flags = stockData.chart.flags || [];

    // 過濾出當前時間之前的正式交易（flag=0）
    const validIndices: number[] = [];
    for (let i = 0; i < timestamps.length; i++) {
      if (timestamps[i] <= currentTime && (flags[i] === 0 || flags[i] === undefined)) {
        validIndices.push(i);
      }
    }

    if (validIndices.length === 0) {
      return stockData.stats;
    }

    // 計算動態統計
    const validPrices = validIndices.map(i => prices[i]);
    const validVolumes = validIndices.map(i => volumes[i]);

    const open_price = validPrices[0];
    const current_price = validPrices[validPrices.length - 1];
    const high_price = Math.max(...validPrices);
    const low_price = Math.min(...validPrices);

    const totalAmount = validIndices.reduce((sum, i) => sum + prices[i] * volumes[i], 0);
    const total_volume = validVolumes.reduce((sum, v) => sum + v, 0);
    const avg_price = total_volume > 0 ? totalAmount / total_volume : 0;

    // 使用前日收盤價計算漲跌（如果有的話）
    const prev_close = stockData.stats.prev_close;
    const basePrice = prev_close ?? open_price;
    const change = current_price - basePrice;
    const change_pct = basePrice > 0 ? (change / basePrice) * 100 : 0;

    return {
      ...stockData.stats,
      current_price,
      open_price,
      high_price,
      low_price,
      avg_price,
      total_volume,
      trade_count: validIndices.length,
      change,
      change_pct,
    };
  }, [stockData, currentTimeIndex]);

  return (
    <header className="bg-black border-b border-gray-800">
      <div className="container mx-auto px-4 py-3">
        {/* 控制列 */}
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-xl font-bold text-yellow-400 font-mono">
            台股即時報價回放系統
          </h1>

          <div className="flex gap-3">
            {/* 日期選擇 */}
            <select
              value={selectedDate || ''}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="px-3 py-1.5 border border-gray-700 rounded bg-black text-white text-sm font-mono focus:ring-1 focus:ring-yellow-400 focus:border-yellow-400"
              disabled={loading}
            >
              <option value="">選擇日期...</option>
              {dates.map((date) => (
                <option key={date} value={date}>
                  {date.slice(0, 4)}/{date.slice(4, 6)}/{date.slice(6, 8)}
                </option>
              ))}
            </select>

            {/* 股票選擇 */}
            <select
              value={selectedStock || ''}
              onChange={(e) => setSelectedStock(e.target.value)}
              disabled={!selectedDate || loading}
              className="px-3 py-1.5 border border-gray-700 rounded bg-black text-white text-sm font-mono focus:ring-1 focus:ring-yellow-400 focus:border-yellow-400 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">選擇股票...</option>
              {stocks.map((stock) => (
                <option key={stock} value={stock}>
                  {stock}
                </option>
              ))}
            </select>

            {/* 重新整理按鈕 */}
            {selectedDate && selectedStock && (
              <button
                onClick={() => {
                  if (selectedDate && selectedStock) {
                    useStockStore.getState().loadStockData(selectedDate, selectedStock);
                  }
                }}
                disabled={loading}
                className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-yellow-400 rounded text-sm font-mono transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
                重整
              </button>
            )}
          </div>
        </div>

        {/* 股票資訊列 */}
        {stockData && stats && (
          <div className="bg-gray-900 border border-gray-800 rounded p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div>
                  <h2 className="text-xl font-bold text-yellow-400 font-mono">
                    {selectedStock}
                  </h2>
                  <p className="text-xs text-gray-500 font-mono">
                    {selectedDate?.slice(0, 4)}/{selectedDate?.slice(4, 6)}/{selectedDate?.slice(6, 8)}
                  </p>
                </div>

                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-white font-mono mono-num">
                    {stats.current_price.toFixed(2)}
                  </span>
                  <span
                    className={`text-base font-bold font-mono mono-num ${
                      stats.change >= 0 ? 'price-up' : 'price-down'
                    }`}
                  >
                    {stats.change >= 0 ? '+' : ''}
                    {stats.change.toFixed(2)} ({stats.change_pct >= 0 ? '+' : ''}
                    {stats.change_pct.toFixed(2)}%)
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-5 gap-4 text-xs">
                <div>
                  <p className="text-gray-500">開盤</p>
                  <p className="font-bold text-white font-mono mono-num">
                    {stats.open_price.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">最高</p>
                  <p className="font-bold price-up font-mono mono-num">
                    {stats.high_price.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">最低</p>
                  <p className="font-bold price-down font-mono mono-num">
                    {stats.low_price.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">均價</p>
                  <p className="font-bold text-white font-mono mono-num">
                    {stats.avg_price.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">成交量</p>
                  <p className="font-bold text-white font-mono mono-num">
                    {(stats.total_volume / 1000).toFixed(0)}K
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
