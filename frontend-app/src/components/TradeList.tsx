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
      <div className="bg-black border border-gray-800 rounded p-6">
        <h3 className="text-sm font-bold mb-4 text-yellow-400">
          成交明細
        </h3>
        <p className="text-gray-400 text-center py-8 text-sm">
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
    <div className="bg-black border border-gray-800 rounded">
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-yellow-400">
            成交明細
          </h3>
          <span className="text-xs text-gray-500 font-mono">
            共 {filteredTrades.length} 筆
          </span>
        </div>
      </div>

      <div className="overflow-y-auto max-h-96">
        <table className="trade-table">
          <thead className="sticky top-0">
            <tr>
              <th className="text-left">時間</th>
              <th className="text-right">價格</th>
              <th className="text-right">單量</th>
              <th className="text-center">內外盤</th>
              <th className="text-center">旗標</th>
            </tr>
          </thead>
          <tbody>
            {displayTrades.map((trade, index) => (
              <tr key={index}>
                <td className="text-left timestamp">
                  {trade.time}
                </td>
                <td
                  className={`text-right font-bold mono-num ${
                    trade.flag === 1
                      ? 'text-gray-500'
                      : trade.inner_outer === '外盤'
                      ? 'price-up'
                      : trade.inner_outer === '內盤'
                      ? 'price-down'
                      : 'text-white'
                  }`}
                >
                  {trade.price.toFixed(2)}
                </td>
                <td className="text-right mono-num text-gray-400">
                  {trade.volume}
                </td>
                <td className="text-center">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs ${
                      trade.flag === 1
                        ? 'bg-gray-800 text-gray-500'
                        : trade.inner_outer === '外盤'
                        ? 'bg-red-900/30 price-up'
                        : trade.inner_outer === '內盤'
                        ? 'bg-green-900/30 price-down'
                        : 'bg-gray-800 text-gray-400'
                    }`}
                  >
                    {trade.inner_outer}
                  </span>
                </td>
                <td className="text-center">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs ${
                      trade.flag === 1
                        ? 'bg-gray-700 text-gray-400'
                        : 'bg-gray-900 text-gray-500'
                    }`}
                  >
                    {trade.flag === 1 ? '試撮' : '正式'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredTrades.length > 20 && (
        <div className="p-3 border-t border-gray-800">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full py-2 px-4 bg-gray-900 hover:bg-gray-800 text-gray-400 hover:text-yellow-400 rounded transition-colors flex items-center justify-center gap-2 text-xs font-mono"
          >
            {expanded ? (
              <>
                <ChevronUp className="w-3 h-3" />
                收起
              </>
            ) : (
              <>
                <ChevronDown className="w-3 h-3" />
                顯示全部 ({filteredTrades.length})
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
