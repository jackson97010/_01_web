import { useState } from 'react';
import type { Trade } from '@/types/stock';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useStockStore } from '@/stores/stockStore';

interface Props {
  trades: Trade[];
}

export default function TradeList({ trades }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { stockData, currentTimeIndex } = useStockStore();

  if (!trades || trades.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
          成交明細
        </h3>
        <p className="text-gray-500 dark:text-gray-400 text-center py-8">
          無成交資料
        </p>
      </div>
    );
  }

  // 根據當前時間過濾成交明細
  const getCurrentTrades = () => {
    if (!stockData?.unifiedTimeline) return trades;

    const currentTime = stockData.unifiedTimeline[currentTimeIndex];
    return trades.filter(trade => trade.time <= currentTime);
  };

  const filteredTrades = getCurrentTrades();
  const displayTrades = expanded ? filteredTrades : filteredTrades.slice(0, 20);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            成交明細
          </h3>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            共 {filteredTrades.length} 筆
          </span>
        </div>
      </div>

      <div className="overflow-y-auto max-h-96">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 dark:bg-gray-700/50 sticky top-0">
            <tr className="text-gray-600 dark:text-gray-400">
              <th className="py-2 px-3 text-left">時間</th>
              <th className="py-2 px-3 text-right">價格</th>
              <th className="py-2 px-3 text-right">單量</th>
              <th className="py-2 px-3 text-center">內外盤</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {displayTrades.map((trade, index) => (
              <tr
                key={index}
                className="hover:bg-gray-50 dark:hover:bg-gray-700/30"
              >
                <td className="py-1.5 px-3 text-left font-mono text-gray-700 dark:text-gray-300">
                  {trade.time}
                </td>
                <td
                  className={`py-1.5 px-3 text-right font-semibold ${
                    trade.inner_outer === '外盤'
                      ? 'text-red-600 dark:text-red-400'
                      : trade.inner_outer === '內盤'
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-gray-700 dark:text-gray-300'
                  }`}
                >
                  {trade.price.toFixed(2)}
                </td>
                <td className="py-1.5 px-3 text-right font-mono text-gray-700 dark:text-gray-300">
                  {trade.volume}
                </td>
                <td className="py-1.5 px-3 text-center">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs ${
                      trade.inner_outer === '外盤'
                        ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                        : trade.inner_outer === '內盤'
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                    }`}
                  >
                    {trade.inner_outer}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredTrades.length > 20 && (
        <div className="p-3 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full py-2 px-4 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm"
          >
            {expanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                收起
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                顯示全部 ({filteredTrades.length} 筆)
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
