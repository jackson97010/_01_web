import type { DepthData } from '@/types/stock';

interface Props {
  depth: DepthData | null;
}

export default function DepthTable({ depth }: Props) {
  if (!depth) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
          五檔報價
        </h3>
        <p className="text-gray-500 dark:text-gray-400 text-center py-8">
          無五檔資料
        </p>
      </div>
    );
  }

  const maxVolume = Math.max(
    ...depth.bids.map((b) => b.volume),
    ...depth.asks.map((a) => a.volume)
  );

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          五檔報價
        </h3>
        {depth.timestamp && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 font-mono">
            更新時間: {depth.timestamp}
          </p>
        )}
      </div>

      <div className="p-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-600 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
              <th className="pb-2 text-left">買量</th>
              <th className="pb-2 text-center">買價</th>
              <th className="pb-2 text-center">賣價</th>
              <th className="pb-2 text-right">賣量</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {[0, 1, 2, 3, 4].map((index) => {
              const bid = depth.bids[index];
              // 賣價正常順序（Ask1 在最上面，Ask5 在最下面）
              const ask = depth.asks[index];

              return (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  {/* 買量 */}
                  <td className="py-2 text-left">
                    {bid && (
                      <div className="relative">
                        <div
                          className="absolute right-0 top-0 bottom-0 bg-red-100 dark:bg-red-900/30 rounded"
                          style={{
                            width: `${(bid.volume / maxVolume) * 100}%`,
                          }}
                        />
                        <span className="relative font-mono text-red-600 dark:text-red-400">
                          {bid.volume}
                        </span>
                      </div>
                    )}
                  </td>

                  {/* 買價 */}
                  <td className="py-2 text-center">
                    {bid && (
                      <span className="font-semibold text-red-600 dark:text-red-400">
                        {bid.price.toFixed(2)}
                      </span>
                    )}
                  </td>

                  {/* 賣價 */}
                  <td className="py-2 text-center">
                    {ask && (
                      <span className="font-semibold text-green-600 dark:text-green-400">
                        {ask.price.toFixed(2)}
                      </span>
                    )}
                  </td>

                  {/* 賣量 */}
                  <td className="py-2 text-right">
                    {ask && (
                      <div className="relative">
                        <div
                          className="absolute left-0 top-0 bottom-0 bg-green-100 dark:bg-green-900/30 rounded"
                          style={{
                            width: `${(ask.volume / maxVolume) * 100}%`,
                          }}
                        />
                        <span className="relative font-mono text-green-600 dark:text-green-400">
                          {ask.volume}
                        </span>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {/* 總量統計 */}
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-between text-xs">
          <div className="text-red-600 dark:text-red-400">
            內盤總量:{' '}
            <span className="font-semibold">
              {depth.bids.reduce((sum, b) => sum + b.volume, 0)}
            </span>
          </div>
          <div className="text-green-600 dark:text-green-400">
            外盤總量:{' '}
            <span className="font-semibold">
              {depth.asks.reduce((sum, a) => sum + a.volume, 0)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
