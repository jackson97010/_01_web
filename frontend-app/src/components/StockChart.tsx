import { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import type { StockData } from '@/types/stock';
import { useStockStore } from '@/stores/stockStore';
import 'chartjs-adapter-date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

interface Props {
  data: StockData;
}

export default function StockChart({ data }: Props) {
  const { chart } = data;
  const { currentTimeIndex, zoomMode } = useStockStore();

  const priceData = useMemo(() => {
    if (!chart || !data.unifiedTimeline) {
      return null;
    }

    // 建立統一時間軸到成交資料的映射
    const tradeTimeMap = new Map(chart.timestamps.map((t, i) => [t, i]));

    // 為統一時間軸的每個時間點找到對應的價格
    const unifiedPrices: (number | null)[] = [];
    const unifiedVwap: (number | null)[] = [];
    const unifiedFlags: (number | null)[] = [];

    for (let i = 0; i <= currentTimeIndex; i++) {
      const time = data.unifiedTimeline[i];
      const tradeIndex = tradeTimeMap.get(time);

      if (tradeIndex !== undefined) {
        // 有成交資料
        unifiedPrices.push(chart.prices[tradeIndex]);
        unifiedVwap.push(chart.vwap[tradeIndex]);
        unifiedFlags.push(chart.flags?.[tradeIndex] ?? 0);
      } else {
        // 沒有成交資料，找最近的前一筆
        let lastPrice = null;
        let lastVwap = null;

        for (let j = i - 1; j >= 0; j--) {
          const prevTime = data.unifiedTimeline[j];
          const prevIndex = tradeTimeMap.get(prevTime);
          if (prevIndex !== undefined) {
            lastPrice = chart.prices[prevIndex];
            lastVwap = chart.vwap[prevIndex];
            break;
          }
        }

        unifiedPrices.push(lastPrice);
        unifiedVwap.push(lastVwap);
        unifiedFlags.push(null);
      }
    }

    let labels, prices, vwapData, flags;

    if (zoomMode === 'dynamic') {
      // 動態模式：只顯示到當前時間
      labels = data.unifiedTimeline.slice(0, currentTimeIndex + 1);
      prices = unifiedPrices;
      vwapData = unifiedVwap;
      flags = unifiedFlags;
    } else {
      // 完整模式：顯示全部時間軸，但只畫到當前時間
      labels = data.unifiedTimeline;
      const nullPadding = new Array(data.unifiedTimeline.length - currentTimeIndex - 1).fill(null);
      prices = [...unifiedPrices, ...nullPadding];
      vwapData = [...unifiedVwap, ...nullPadding];
      flags = [...unifiedFlags, ...nullPadding];
    }

    // 設定每個點的樣式：根據 flag 區分試撮和正式交易
    const pointRadii = new Array(labels.length).fill(0);
    const pointColors = new Array(labels.length).fill('rgb(59, 130, 246)');
    const endIndex = currentTimeIndex + 1;

    // 為試撮的點設定標記
    for (let i = 0; i < flags.length; i++) {
      if (flags[i] === 1) {
        pointRadii[i] = 3;
        pointColors[i] = 'rgba(128, 128, 128, 0.6)'; // 灰色標記試撮
      }
    }

    // 為最後一個有效點設定紅點
    if (endIndex <= labels.length) {
      pointRadii[endIndex - 1] = 6;
      pointColors[endIndex - 1] = 'rgb(239, 68, 68)';
    }

    return {
      labels,
      datasets: [
        {
          label: '價格',
          data: prices,
          borderColor: '#ffff00',
          backgroundColor: 'rgba(255, 255, 0, 0.1)',
          borderWidth: 2,
          pointRadius: pointRadii,
          pointBackgroundColor: pointColors,
          pointBorderColor: pointColors,
          pointBorderWidth: 2,
          tension: 0.1,
          yAxisID: 'y',
          spanGaps: false,
        },
        {
          label: 'VWAP',
          data: vwapData,
          borderColor: '#00ffff',
          backgroundColor: 'rgba(0, 255, 255, 0.1)',
          borderWidth: 2,
          pointRadius: 0,
          borderDash: [5, 5],
          tension: 0.1,
          yAxisID: 'y',
          spanGaps: false,
        },
      ],
    };
  }, [chart, data, currentTimeIndex, zoomMode]);

  const volumeData = useMemo(() => {
    if (!chart || !data.unifiedTimeline) return null;

    // 建立統一時間軸到成交資料的映射
    const tradeTimeMap = new Map(chart.timestamps.map((t, i) => [t, i]));

    // 每分鐘累積成交量，但逐 tick 增長
    const minuteVolumeMap = new Map<string, number>();

    // 計算範圍根據 zoomMode
    const endIndex = zoomMode === 'dynamic' ? currentTimeIndex : data.unifiedTimeline.length - 1;

    // 收集所有分鐘（包括未來的）
    const allMinutes = new Set<string>();
    for (let i = 0; i <= endIndex; i++) {
      const time = data.unifiedTimeline[i];
      const minute = time.substring(0, 16);
      allMinutes.add(minute);
      if (!minuteVolumeMap.has(minute)) {
        minuteVolumeMap.set(minute, 0);
      }
    }

    // 只累積到當前時間為止的成交量
    for (let i = 0; i <= currentTimeIndex; i++) {
      const time = data.unifiedTimeline[i];
      const minute = time.substring(0, 16);
      const tradeIndex = tradeTimeMap.get(time);

      // 累積該分鐘的成交量（只計算 flag=0 的正式交易）
      if (tradeIndex !== undefined && (chart.flags?.[tradeIndex] ?? 0) === 0) {
        const currentVol = minuteVolumeMap.get(minute) || 0;
        minuteVolumeMap.set(minute, currentVol + (chart.volumes[tradeIndex] || 0));
      }
    }

    // 轉為排序後的陣列
    const sortedMinutes = Array.from(allMinutes).sort();
    const minuteLabels: string[] = [];
    const minuteVolumes: (number | null)[] = [];

    const currentMinute = data.unifiedTimeline[currentTimeIndex].substring(0, 16);

    sortedMinutes.forEach(minute => {
      minuteLabels.push(minute);

      if (minute <= currentMinute) {
        // 已經播放過的分鐘，顯示累積值
        minuteVolumes.push(minuteVolumeMap.get(minute) || 0);
      } else {
        // 還沒播放到的分鐘，顯示 null（不顯示柱狀圖）
        minuteVolumes.push(null);
      }
    });

    return {
      labels: minuteLabels,
      datasets: [
        {
          label: '每分鐘成交量',
          data: minuteVolumes,
          backgroundColor: 'rgba(255, 0, 255, 0.6)',
          borderColor: '#ff00ff',
          borderWidth: 1,
        },
      ],
    };
  }, [chart, data, currentTimeIndex, zoomMode]);

  const priceOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false as const,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: '#888888',
          font: {
            family: 'Consolas, Monaco, monospace',
            size: 11,
          },
        },
      },
      title: {
        display: false,
      },
      tooltip: {
        backgroundColor: '#1a1a1a',
        titleColor: '#ffffff',
        bodyColor: '#ffffff',
        borderColor: '#333333',
        borderWidth: 1,
        callbacks: {
          label: function (context: any) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += context.parsed.y.toFixed(2);
            }
            return label;
          },
        },
      },
    },
    scales: {
      x: {
        type: 'time' as const,
        time: {
          unit: 'minute' as const,
          displayFormats: {
            minute: 'HH:mm',
          },
        },
        grid: {
          color: '#1a1a1a',
        },
        ticks: {
          color: '#888888',
          font: {
            family: 'Consolas, Monaco, monospace',
            size: 10,
          },
        },
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        grid: {
          color: '#1a1a1a',
        },
        ticks: {
          color: '#888888',
          font: {
            family: 'Consolas, Monaco, monospace',
            size: 10,
          },
        },
      },
    },
  };

  const volumeOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false as const,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: false,
      },
      tooltip: {
        backgroundColor: '#1a1a1a',
        titleColor: '#ffffff',
        bodyColor: '#ffffff',
        borderColor: '#333333',
        borderWidth: 1,
        callbacks: {
          label: function (context: any) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += context.parsed.y.toLocaleString();
            }
            return label;
          },
        },
      },
    },
    scales: {
      x: {
        type: 'time' as const,
        time: {
          unit: 'minute' as const,
          displayFormats: {
            minute: 'HH:mm',
          },
        },
        grid: {
          color: '#1a1a1a',
        },
        ticks: {
          color: '#888888',
          font: {
            family: 'Consolas, Monaco, monospace',
            size: 10,
          },
        },
      },
      y: {
        type: 'linear' as const,
        grid: {
          color: '#1a1a1a',
        },
        ticks: {
          color: '#888888',
          font: {
            family: 'Consolas, Monaco, monospace',
            size: 10,
          },
        },
      },
    },
  };

  if (!chart) {
    return (
      <div className="bg-black border border-gray-800 rounded p-6">
        <p className="text-gray-400 text-center text-sm">無圖表資料</p>
      </div>
    );
  }

  if (!data.unifiedTimeline) {
    return (
      <div className="bg-black border border-gray-800 rounded p-6">
        <p className="text-gray-400 text-center text-sm">統一時間軸尚未建立</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 價格圖表 */}
      <div className="bg-black border border-gray-800 rounded p-4">
        <h3 className="text-sm font-bold text-yellow-400 mb-3 font-mono">價格走勢與 VWAP</h3>
        <div className="h-96">
          {priceData ? (
            <Line options={priceOptions} data={priceData} />
          ) : (
            <p className="text-gray-400 text-center py-20 text-sm">無法計算價格資料</p>
          )}
        </div>
      </div>

      {/* 成交量圖表 */}
      <div className="bg-black border border-gray-800 rounded p-4">
        <h3 className="text-sm font-bold text-yellow-400 mb-3 font-mono">每分鐘成交量</h3>
        <div className="h-48">
          {volumeData ? (
            <Bar options={volumeOptions} data={volumeData} />
          ) : (
            <p className="text-gray-400 text-center py-10 text-sm">無法計算成交量資料</p>
          )}
        </div>
      </div>
    </div>
  );
}
