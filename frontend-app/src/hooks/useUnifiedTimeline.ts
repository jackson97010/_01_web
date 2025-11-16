import { useMemo } from 'react';
import type { StockData } from '@/types/stock';

/**
 * 統一時間軸 Hook
 * 將成交資料和五檔資料合併成統一的時間軸
 */
export function useUnifiedTimeline(stockData: StockData | null) {
  return useMemo(() => {
    if (!stockData) return null;

    // 收集所有時間戳
    const timeSet = new Set<string>();

    // 添加成交資料的時間
    if (stockData.chart?.timestamps) {
      stockData.chart.timestamps.forEach(t => timeSet.add(t));
    }

    // 添加五檔資料的時間
    if (stockData.depth_history) {
      stockData.depth_history.forEach(d => timeSet.add(d.timestamp));
    }

    // 排序所有時間戳
    const unifiedTimestamps = Array.from(timeSet).sort();

    // 為每個時間點建立對應的資料索引
    const timelineData = unifiedTimestamps.map((timestamp) => {
      // 找到對應的成交資料索引
      let tradeIndex = -1;
      if (stockData.chart?.timestamps) {
        tradeIndex = stockData.chart.timestamps.findIndex(t => t === timestamp);
        // 如果找不到精確匹配，找最近的前一筆
        if (tradeIndex === -1) {
          for (let i = stockData.chart.timestamps.length - 1; i >= 0; i--) {
            if (stockData.chart.timestamps[i] <= timestamp) {
              tradeIndex = i;
              break;
            }
          }
        }
      }

      // 找到對應的五檔資料索引
      let depthIndex = -1;
      if (stockData.depth_history) {
        depthIndex = stockData.depth_history.findIndex(d => d.timestamp === timestamp);
        // 如果找不到精確匹配，找最近的前一筆
        if (depthIndex === -1) {
          for (let i = stockData.depth_history.length - 1; i >= 0; i--) {
            if (stockData.depth_history[i].timestamp <= timestamp) {
              depthIndex = i;
              break;
            }
          }
        }
      }

      return {
        timestamp,
        tradeIndex,
        depthIndex,
      };
    });

    return {
      timestamps: unifiedTimestamps,
      data: timelineData,
    };
  }, [stockData]);
}

/**
 * 根據統一時間軸索引獲取當前五檔資料
 */
export function getCurrentDepthByTimeline(
  stockData: StockData | null,
  unifiedTimeIndex: number
) {
  if (!stockData?.depth_history || stockData.depth_history.length === 0) {
    return stockData?.depth || null;
  }

  // 使用統一時間軸獲取當前時間
  const timeline = useUnifiedTimeline(stockData);
  if (!timeline || unifiedTimeIndex >= timeline.timestamps.length) {
    return stockData.depth_history[stockData.depth_history.length - 1];
  }

  const currentTime = timeline.timestamps[unifiedTimeIndex];

  // 找到最接近且不晚於當前時間的五檔資料
  let selectedDepth = stockData.depth_history[0];

  for (const depth of stockData.depth_history) {
    if (depth.timestamp <= currentTime) {
      selectedDepth = depth;
    } else {
      break;
    }
  }

  return selectedDepth;
}
