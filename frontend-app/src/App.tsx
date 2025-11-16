import { useEffect } from 'react';
import { useStockStore } from '@/stores/stockStore';
import Header from '@/components/Header';
import StockChart from '@/components/StockChart';
import DepthTable from '@/components/DepthTable';
import TradeList from '@/components/TradeList';
import TimelineControls from '@/components/TimelineControls';
import '@/styles/index.css';

function App() {
  const { loadDates, stockData, loading, error, currentTimeIndex } = useStockStore();

  useEffect(() => {
    loadDates();
  }, [loadDates]);

  // 根據當前時間索引獲取對應的五檔資料
  const getCurrentDepth = () => {
    if (!stockData || !stockData.depth_history || stockData.depth_history.length === 0) {
      return stockData?.depth || null;
    }

    if (!stockData.unifiedTimeline) {
      return stockData?.depth || null;
    }

    // 從統一時間軸獲取當前時間
    const currentTime = stockData.unifiedTimeline[currentTimeIndex];

    // 在 depth_history 中找到最接近且不晚於當前時間的五檔資料
    let selectedDepth = stockData.depth_history[0];

    for (const depth of stockData.depth_history) {
      if (depth.timestamp <= currentTime) {
        selectedDepth = depth;
      } else {
        break;
      }
    }

    return selectedDepth;
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 頂部導航欄 */}
      <Header />

      {/* 主要內容區 */}
      <main className="container mx-auto px-4 py-6">
        {loading && (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {!loading && !error && stockData && (
          <div className="space-y-6">
            {/* 時間軸控制 */}
            <TimelineControls />

            {/* 主要內容 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* 左側：圖表區 */}
              <div className="lg:col-span-2 space-y-6">
                <StockChart data={stockData} />
              </div>

              {/* 右側：五檔與成交明細 */}
              <div className="space-y-6">
                <DepthTable depth={getCurrentDepth()} />
                <TradeList trades={stockData.trades} />
              </div>
            </div>
          </div>
        )}

        {!loading && !error && !stockData && (
          <div className="text-center py-12">
            <p className="text-gray-500 dark:text-gray-400 text-lg">
              請選擇日期和股票代碼開始查看
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
