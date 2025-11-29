import type { DepthData } from '@/types/stock';

interface Props {
  depth: DepthData | null;
}

export default function DepthTable({ depth }: Props) {
  if (!depth) {
    return (
      <div className="bg-black rounded border border-gray-800 p-6">
        <h3 className="text-sm font-bold mb-4 text-yellow-400">
          五檔報價
        </h3>
        <p className="text-gray-400 text-center py-8 text-sm">
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
    <div className="bg-black rounded border border-gray-800">
      <div className="p-3 border-b border-gray-800">
        <h3 className="text-sm font-bold text-yellow-400">
          五檔報價
        </h3>
        {depth.timestamp && (
          <p className="timestamp mt-1">
            更新: {depth.timestamp}
          </p>
        )}
      </div>

      <div className="p-3">
        <table className="depth-table">
          <thead>
            <tr>
              <th className="text-left">買量</th>
              <th className="text-center">買價</th>
              <th className="text-center">賣價</th>
              <th className="text-right">賣量</th>
            </tr>
          </thead>
          <tbody>
            {[0, 1, 2, 3, 4].map((index) => {
              const bid = depth.bids[index];
              const ask = depth.asks[index];

              return (
                <tr key={index}>
                  {/* 買量 */}
                  <td className="text-left">
                    {bid && (
                      <div className="relative">
                        <div
                          className="bid-bar absolute right-0 top-0 bottom-0"
                          style={{
                            width: `${(bid.volume / maxVolume) * 100}%`,
                          }}
                        />
                        <span className="relative bid-volume mono-num">
                          {bid.volume}
                        </span>
                      </div>
                    )}
                  </td>

                  {/* 買價 */}
                  <td className="text-center">
                    {bid && (
                      <span className="bid-price mono-num">
                        {bid.price === 0 || bid.price < 0.01 ? '市價' : bid.price.toFixed(2)}
                      </span>
                    )}
                  </td>

                  {/* 賣價 */}
                  <td className="text-center">
                    {ask && (
                      <span className="ask-price mono-num">
                        {ask.price === 0 || ask.price < 0.01 ? '市價' : ask.price.toFixed(2)}
                      </span>
                    )}
                  </td>

                  {/* 賣量 */}
                  <td className="text-right">
                    {ask && (
                      <div className="relative">
                        <div
                          className="ask-bar absolute left-0 top-0 bottom-0"
                          style={{
                            width: `${(ask.volume / maxVolume) * 100}%`,
                          }}
                        />
                        <span className="relative ask-volume mono-num">
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
        <div className="mt-3 pt-3 border-t border-gray-800 flex justify-between text-xs">
          <div className="bid-volume">
            內盤總量:{' '}
            <span className="font-bold mono-num">
              {depth.bids.reduce((sum, b) => sum + b.volume, 0)}
            </span>
          </div>
          <div className="ask-volume">
            外盤總量:{' '}
            <span className="font-bold mono-num">
              {depth.asks.reduce((sum, a) => sum + a.volume, 0)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
