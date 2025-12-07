import { useEffect, useRef, useMemo } from 'react';
import { createChart, ColorType, IChartApi, LineStyle } from 'lightweight-charts';
import type { StockData } from '@/types/stock';
import { useStockStore } from '@/stores/stockStore';

interface Props {
  data: StockData;
}

export default function LightweightStockChart({ data }: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const priceSeriesRef = useRef<any>(null);
  const vwapSeriesRef = useRef<any>(null);
  const volumeSeriesRef = useRef<any>(null);

  const { currentTimeIndex, zoomMode } = useStockStore();

  // 準備價格資料
  const chartData = useMemo(() => {
    if (!data.chart || !data.unifiedTimeline) return null;

    // 過濾函數：只保留 09:00 之後的時間
    const filterTime = (timeStr: string) => {
      const timePart = timeStr.split(' ')[1];
      if (!timePart) return false;
      const hour = parseInt(timePart.split(':')[0]);
      return hour >= 9;
    };

    const tradeTimeMap = new Map(data.chart.timestamps.map((t, i) => [t, i]));
    const priceData: { time: string; value: number }[] = [];
    const vwapData: { time: string; value: number }[] = [];
    const volumeData: { time: string; value: number; color: string }[] = [];

    // 準備每分鐘累積成交量
    // 注意：後端已經處理好 flag 的邏輯，flag=1 的成交量不會計入 total_volumes
    const minuteMap = new Map<string, number>();
    data.chart.timestamps.forEach((timestamp, index) => {
      const minute = timestamp.substring(0, 16).replace(' ', 'T'); // 轉換為 ISO 格式
      const currentVolume = data.chart!.volumes[index] || 0;
      const flag = data.chart!.flags?.[index] ?? 0;
      // 只累加 flag=0 的成交量
      if (flag === 0) {
        minuteMap.set(minute, (minuteMap.get(minute) || 0) + currentVolume);
      }
    });

    let cumulative = 0;
    let lastMinute = '';
    const endIndex = zoomMode === 'dynamic' ? currentTimeIndex + 1 : data.unifiedTimeline.length;

    for (let i = 0; i < endIndex; i++) {
      const time = data.unifiedTimeline[i];

      // 跳過 09:00 之前的時間點
      if (!filterTime(time)) {
        continue;
      }

      const isoTime = time.substring(0, 16).replace(' ', 'T'); // 轉換為 ISO 格式
      const minute = time.substring(0, 16).replace(' ', 'T');
      const tradeIndex = tradeTimeMap.get(time);

      // 檢查是否進入新的分鐘
      if (minute !== lastMinute && minuteMap.has(minute)) {
        cumulative += minuteMap.get(minute)!;
        lastMinute = minute;
      }

      if (tradeIndex !== undefined) {
        const price = data.chart.prices[tradeIndex];
        const vwap = data.chart.vwap[tradeIndex];

        priceData.push({ time: isoTime, value: price });
        vwapData.push({ time: isoTime, value: vwap });

        // 成交量使用柱狀圖，綠色表示
        volumeData.push({
          time: isoTime,
          value: cumulative,
          color: 'rgba(34, 197, 94, 0.6)',
        });
      } else {
        // 沒有成交資料時，找最近的前一筆價格
        let lastPrice = null;
        let lastVwap = null;

        for (let j = i - 1; j >= 0; j--) {
          const prevTime = data.unifiedTimeline[j];
          const prevIndex = tradeTimeMap.get(prevTime);
          if (prevIndex !== undefined) {
            lastPrice = data.chart.prices[prevIndex];
            lastVwap = data.chart.vwap[prevIndex];
            break;
          }
        }

        if (lastPrice !== null) {
          priceData.push({ time: isoTime, value: lastPrice });
        }
        if (lastVwap !== null) {
          vwapData.push({ time: isoTime, value: lastVwap });
        }
      }
    }

    return { priceData, vwapData, volumeData };
  }, [data, currentTimeIndex, zoomMode]);

  // 初始化圖表
  useEffect(() => {
    if (!chartContainerRef.current || !chartData) return;

    // 創建圖表
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#000000' },
        textColor: '#ffffff',
      },
      grid: {
        vertLines: { color: '#1a1a1a' },
        horzLines: { color: '#1a1a1a' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
      timeScale: {
        timeVisible: true,
        secondsVisible: true,
        borderColor: '#1a1a1a',
      },
      rightPriceScale: {
        borderColor: '#1a1a1a',
      },
    });

    chartRef.current = chart;

    // 價格線（黃色）
    const priceSeries = (chart as any).addLineSeries({
      color: '#ffff00',
      lineWidth: 2,
    });
    priceSeriesRef.current = priceSeries;
    priceSeries.setData(chartData.priceData);

    // VWAP 線（青色，虛線）
    const vwapSeries = (chart as any).addLineSeries({
      color: '#00ffff',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
    });
    vwapSeriesRef.current = vwapSeries;
    vwapSeries.setData(chartData.vwapData);

    // 成交量柱狀圖（紫色）
    const volumeSeries = (chart as any).addHistogramSeries({
      color: '#ff00ff',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
    });
    volumeSeriesRef.current = volumeSeries;
    volumeSeries.setData(chartData.volumeData);

    // 設置成交量的價格刻度
    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.7,
        bottom: 0,
      },
    });

    // 設定時間軸範圍（只顯示有資料的範圍）
    if (chartData.priceData.length > 0) {
      const firstTime = chartData.priceData[0].time;
      const lastTime = chartData.priceData[chartData.priceData.length - 1].time;

      // 設定可見範圍從第一個資料點開始
      chart.timeScale().setVisibleRange({
        from: firstTime as any,
        to: lastTime as any,
      });
    }

    // 響應式
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [chartData]);

  // 更新圖表資料（當 currentTimeIndex 改變時）
  useEffect(() => {
    if (!chartData || !priceSeriesRef.current || !vwapSeriesRef.current || !volumeSeriesRef.current || !chartRef.current) return;

    priceSeriesRef.current.setData(chartData.priceData);
    vwapSeriesRef.current.setData(chartData.vwapData);
    volumeSeriesRef.current.setData(chartData.volumeData);

    // 更新時間軸範圍
    if (chartData.priceData.length > 0 && zoomMode === 'full') {
      const firstTime = chartData.priceData[0].time;
      const lastTime = chartData.priceData[chartData.priceData.length - 1].time;

      chartRef.current.timeScale().setVisibleRange({
        from: firstTime as any,
        to: lastTime as any,
      });
    }
  }, [chartData, zoomMode]);

  if (!data.chart) {
    return (
      <div className="bg-black rounded-lg shadow p-6 border border-gray-800">
        <p className="text-gray-400 text-center font-mono">無圖表資料</p>
      </div>
    );
  }

  if (!data.unifiedTimeline) {
    return (
      <div className="bg-black rounded-lg shadow p-6 border border-gray-800">
        <p className="text-gray-400 text-center font-mono">統一時間軸尚未建立</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 圖表容器 */}
      <div className="bg-black rounded-lg shadow p-6 border border-gray-800">
        <h3 className="text-yellow-400 font-bold mb-4 font-mono text-sm">
          價格走勢與成交量
        </h3>
        <div ref={chartContainerRef} className="w-full" />
      </div>
    </div>
  );
}
