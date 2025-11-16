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
    const currentTime = data.unifiedTimeline[currentTimeIndex];
    const tradeTimeMap = new Map(chart.timestamps.map((t, i) => [t, i]));
    const endIndex = currentTimeIndex + 1;

    // 為統一時間軸的每個時間點找到對應的價格
    const unifiedPrices: (number | null)[] = [];
    const unifiedVwap: (number | null)[] = [];

    for (let i = 0; i <= currentTimeIndex; i++) {
      const time = data.unifiedTimeline[i];
      const tradeIndex = tradeTimeMap.get(time);

      if (tradeIndex !== undefined) {
        // 有成交資料
        unifiedPrices.push(chart.prices[tradeIndex]);
        unifiedVwap.push(chart.vwap[tradeIndex]);
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
      }
    }

    let labels, prices, vwapData;

    if (zoomMode === 'dynamic') {
      // 動態模式：只顯示到當前時間
      labels = data.unifiedTimeline.slice(0, currentTimeIndex + 1);
      prices = unifiedPrices;
      vwapData = unifiedVwap;
    } else {
      // 完整模式：顯示全部時間軸，但只畫到當前時間
      labels = data.unifiedTimeline;
      const nullPadding = new Array(data.unifiedTimeline.length - currentTimeIndex - 1).fill(null);
      prices = [...unifiedPrices, ...nullPadding];
      vwapData = [...unifiedVwap, ...nullPadding];
    }

    // 為最後一個有效點設定紅點
    const pointRadii = new Array(labels.length).fill(0);
    const pointColors = new Array(labels.length).fill('rgb(59, 130, 246)');

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
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
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
          borderColor: 'rgb(168, 85, 247)',
          backgroundColor: 'rgba(168, 85, 247, 0.1)',
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

    const endIndex = currentTimeIndex + 1;
    let labels, volumes;

    // 建立成交時間到索引的映射
    const tradeTimeMap = new Map(chart.timestamps.map((t, i) => [t, i]));

    // 先計算成交資料的每分鐘累積成交量
    const minuteMap = new Map<string, number>();
    chart.timestamps.forEach((timestamp, index) => {
      const minute = timestamp.substring(0, 16);
      const currentVolume = chart.volumes[index] || 0;
      minuteMap.set(minute, (minuteMap.get(minute) || 0) + currentVolume);
    });

    // 為統一時間軸的每個時間點計算累積成交量
    const unifiedVolumes: (number | null)[] = [];
    let cumulative = 0;
    let lastMinute = '';

    for (let i = 0; i <= currentTimeIndex; i++) {
      const time = data.unifiedTimeline[i];
      const minute = time.substring(0, 16);
      const tradeIndex = tradeTimeMap.get(time);

      // 檢查是否進入新的分鐘
      if (minute !== lastMinute && minuteMap.has(minute)) {
        cumulative += minuteMap.get(minute)!;
        lastMinute = minute;
      }

      // 如果這個時間點有成交，顯示累積量；否則顯示 null
      if (tradeIndex !== undefined) {
        unifiedVolumes.push(cumulative);
      } else {
        unifiedVolumes.push(null);
      }
    }

    if (zoomMode === 'dynamic') {
      // 動態模式：只顯示到當前時間
      labels = data.unifiedTimeline.slice(0, currentTimeIndex + 1);
      volumes = unifiedVolumes;
    } else {
      // 完整模式：顯示全部時間軸，但只畫到當前時間
      labels = data.unifiedTimeline;
      const nullPadding = new Array(data.unifiedTimeline.length - currentTimeIndex - 1).fill(null);
      volumes = [...unifiedVolumes, ...nullPadding];
    }

    return {
      labels,
      datasets: [
        {
          label: '每分鐘累積成交量',
          data: volumes,
          backgroundColor: 'rgba(34, 197, 94, 0.6)',
          borderColor: 'rgb(34, 197, 94)',
          borderWidth: 1,
        },
      ],
    };
  }, [chart, data, currentTimeIndex, zoomMode]);

  const priceOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false, // 停用動畫以提升效能
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: '價格走勢',
      },
      tooltip: {
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
        title: {
          display: true,
          text: '時間',
        },
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: '價格',
        },
      },
    },
  };

  const volumeOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false, // 停用動畫以提升效能
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: '成交量',
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
        display: false,
      },
      y: {
        type: 'linear' as const,
        title: {
          display: true,
          text: '張數',
        },
      },
    },
  };

  if (!chart) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <p className="text-gray-500 dark:text-gray-400 text-center">無圖表資料</p>
      </div>
    );
  }

  if (!data.unifiedTimeline) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <p className="text-gray-500 dark:text-gray-400 text-center">統一時間軸尚未建立</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 價格圖表 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="h-96">
          {priceData ? (
            <Line options={priceOptions} data={priceData} />
          ) : (
            <p className="text-gray-500 dark:text-gray-400 text-center py-20">無法計算價格資料</p>
          )}
        </div>
      </div>

      {/* 成交量圖表 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="h-48">
          {volumeData ? (
            <Bar options={volumeOptions} data={volumeData} />
          ) : (
            <p className="text-gray-500 dark:text-gray-400 text-center py-10">無法計算成交量資料</p>
          )}
        </div>
      </div>
    </div>
  );
}
