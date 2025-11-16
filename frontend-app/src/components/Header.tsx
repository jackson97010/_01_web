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
  } = useStockStore();

  const stats = stockData?.stats;

  return (
    <header className="bg-white dark:bg-gray-800 shadow-md">
      <div className="container mx-auto px-4 py-4">
        {/* 控制列 */}
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            📊 Stock Quote Viewer
          </h1>

          <div className="flex gap-3">
            {/* 日期選擇 */}
            <select
              value={selectedDate || ''}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
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
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                重新整理
              </button>
            )}
          </div>
        </div>

        {/* 股票資訊列 */}
        {stockData && stats && (
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                    {selectedStock}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {selectedDate?.slice(0, 4)}/{selectedDate?.slice(4, 6)}/{selectedDate?.slice(6, 8)}
                  </p>
                </div>

                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-gray-900 dark:text-white">
                    {stats.current_price.toFixed(2)}
                  </span>
                  <span
                    className={`text-lg font-semibold ${
                      stats.change >= 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-green-600 dark:text-green-400'
                    }`}
                  >
                    {stats.change >= 0 ? '+' : ''}
                    {stats.change.toFixed(2)} ({stats.change_pct >= 0 ? '+' : ''}
                    {stats.change_pct.toFixed(2)}%)
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-5 gap-6 text-sm">
                <div>
                  <p className="text-gray-500 dark:text-gray-400">開盤</p>
                  <p className="font-semibold text-gray-900 dark:text-white">
                    {stats.open_price.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 dark:text-gray-400">最高</p>
                  <p className="font-semibold text-red-600 dark:text-red-400">
                    {stats.high_price.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 dark:text-gray-400">最低</p>
                  <p className="font-semibold text-green-600 dark:text-green-400">
                    {stats.low_price.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 dark:text-gray-400">均價</p>
                  <p className="font-semibold text-gray-900 dark:text-white">
                    {stats.avg_price.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 dark:text-gray-400">成交量</p>
                  <p className="font-semibold text-gray-900 dark:text-white">
                    {(stats.total_volume / 1000).toFixed(0)}K 張
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
