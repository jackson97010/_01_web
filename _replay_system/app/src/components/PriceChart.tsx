import React, { useEffect, useRef, useMemo, memo } from 'react';
import * as echarts from 'echarts';
import { TradeRow } from '../types';

interface PriceChartProps {
  trades: TradeRow[];
  currentTimestamp: number;
}

const PriceChart: React.FC<PriceChartProps> = memo(({ trades, currentTimestamp }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  // 過濾並準備數據：只顯示到當前時間戳記的成交數據
  const chartData = useMemo(() => {
    // 過濾出時間戳記小於等於 currentTimestamp 的成交
    const visibleTrades = trades.filter(trade =>
      (trade.Timestamp || 0) <= currentTimestamp
    );

    // 只取從 09:00 開始的數據
    const filteredTrades = visibleTrades.filter(trade => {
      const dt = trade.Datetime instanceof Date ? trade.Datetime : new Date(trade.Datetime);
      const hour = dt.getHours();
      return hour >= 9;
    });

    // 如果數據點太多（超過 5000 點），進行降採樣
    const maxPoints = 5000;
    const step = Math.max(1, Math.floor(filteredTrades.length / maxPoints));

    const sampledTrades = step > 1
      ? filteredTrades.filter((_, i) => i % step === 0 || i === filteredTrades.length - 1)
      : filteredTrades;

    return sampledTrades.map(trade => {
      const dt = trade.Datetime instanceof Date ? trade.Datetime : new Date(trade.Datetime);
      return {
        time: dt.getTime(),
        price: Number(trade.Price || 0),
        volume: Number(trade.Volume || 0),
        flag: trade.BS_Flag
      };
    });
  }, [trades, currentTimestamp]);

  useEffect(() => {
    if (!chartRef.current) return;

    // 初始化圖表
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, 'dark');
    }

    // 處理視窗大小變化
    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    const chart = chartInstance.current;

    // 準備數據
    const times = chartData.map(d => d.time);
    const prices = chartData.map(d => d.price);
    const volumes = chartData.map(d => d.volume);

    // 計算價格範圍
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice;
    const padding = priceRange * 0.1;

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      grid: [
        {
          left: '3%',
          right: '3%',
          top: '5%',
          height: '65%',
          containLabel: true
        },
        {
          left: '3%',
          right: '3%',
          top: '75%',
          height: '18%',
          containLabel: true
        }
      ],
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        },
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          const dataIndex = params[0].dataIndex;
          const data = chartData[dataIndex];
          const time = new Date(data.time);
          const timeStr = `${time.getHours().toString().padStart(2, '0')}:${time.getMinutes().toString().padStart(2, '0')}:${time.getSeconds().toString().padStart(2, '0')}.${time.getMilliseconds().toString().padStart(3, '0')}`;
          const flag = data.flag === 'Out' ? '外盤' : data.flag === 'In' ? '內盤' : '--';
          const flagColor = data.flag === 'Out' ? '#ff4d4f' : data.flag === 'In' ? '#00c853' : '#888';

          return `
            <div style="padding: 5px;">
              <div>${timeStr}</div>
              <div>價格: <strong>${data.price.toFixed(2)}</strong></div>
              <div>量: ${data.volume}</div>
              <div style="color: ${flagColor}">類型: ${flag}</div>
            </div>
          `;
        }
      },
      xAxis: [
        {
          type: 'time',
          gridIndex: 0,
          axisLabel: {
            formatter: (value: number) => {
              const date = new Date(value);
              return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            },
            color: '#888'
          },
          axisLine: {
            lineStyle: { color: '#333' }
          },
          splitLine: {
            show: true,
            lineStyle: { color: '#1a1a1a' }
          }
        },
        {
          type: 'time',
          gridIndex: 1,
          axisLabel: {
            formatter: (value: number) => {
              const date = new Date(value);
              return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            },
            color: '#888'
          },
          axisLine: {
            lineStyle: { color: '#333' }
          }
        }
      ],
      yAxis: [
        {
          type: 'value',
          gridIndex: 0,
          scale: true,
          min: minPrice - padding,
          max: maxPrice + padding,
          axisLabel: {
            color: '#888',
            formatter: (value: number) => value.toFixed(2)
          },
          axisLine: {
            lineStyle: { color: '#333' }
          },
          splitLine: {
            lineStyle: { color: '#1a1a1a' }
          }
        },
        {
          type: 'value',
          gridIndex: 1,
          axisLabel: {
            color: '#888'
          },
          axisLine: {
            lineStyle: { color: '#333' }
          },
          splitLine: {
            show: false
          }
        }
      ],
      series: [
        {
          name: '價格',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: times.map((time, i) => [time, prices[i]]),
          smooth: false,
          symbol: 'circle',
          symbolSize: 3,
          lineStyle: {
            width: 2,
            color: '#1890ff'
          },
          itemStyle: {
            color: '#1890ff'
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
              { offset: 1, color: 'rgba(24, 144, 255, 0.05)' }
            ])
          }
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: times.map((time, i) => [time, volumes[i]]),
          itemStyle: {
            color: 'rgba(24, 144, 255, 0.6)'
          }
        }
      ]
    };

    // 使用 notMerge: false 和 lazyUpdate: true 來提升性能
    chart.setOption(option, {
      notMerge: false,  // 不合併，直接替換（更快）
      lazyUpdate: true  // 延遲更新
    });

    // 響應式調整
    const handleResize = () => {
      chart.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [chartData]);

  // 清理
  useEffect(() => {
    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, []);

  return (
    <div style={{ width: '100%', height: '100%', minHeight: '400px' }}>
      <div ref={chartRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
});

export default PriceChart;
