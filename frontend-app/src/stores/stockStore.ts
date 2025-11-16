import { create } from 'zustand';
import type { StockData } from '@/types/stock';
import { stockAPI } from '@/services/api';

interface StockStore {
  // 狀態
  dates: string[];
  stocks: string[];
  selectedDate: string | null;
  selectedStock: string | null;
  stockData: StockData | null;
  loading: boolean;
  error: string | null;

  // 回放狀態
  isPlaying: boolean;
  playbackSpeed: number;
  currentTimeIndex: number;

  // 圖表顯示模式
  zoomMode: 'dynamic' | 'full'; // dynamic: 動態縮放, full: 完整時間軸

  // 時間軸密度（毫秒間隔，0 = 不過濾）
  timelineInterval: number;

  // 動作
  loadDates: () => Promise<void>;
  loadStocks: (date: string) => Promise<void>;
  loadStockData: (date: string, stockCode: string) => Promise<void>;
  setSelectedDate: (date: string | null) => void;
  setSelectedStock: (stock: string | null) => void;

  // 回放控制
  togglePlayback: () => void;
  setPlaybackSpeed: (speed: number) => void;
  setCurrentTimeIndex: (index: number) => void;
  toggleZoomMode: () => void;
}

export const useStockStore = create<StockStore>((set, get) => ({
  // 初始狀態
  dates: [],
  stocks: [],
  selectedDate: null,
  selectedStock: null,
  stockData: null,
  loading: false,
  error: null,

  isPlaying: false,
  playbackSpeed: 1,
  currentTimeIndex: 0,
  zoomMode: 'dynamic',
  timelineInterval: 0, // 0 = 不過濾，100 = 每100ms取一個點

  // 載入日期清單
  loadDates: async () => {
    set({ loading: true, error: null });
    try {
      const dates = await stockAPI.getDates();
      set({ dates, loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '載入日期失敗',
        loading: false
      });
    }
  },

  // 載入股票清單
  loadStocks: async (date: string) => {
    set({ loading: true, error: null });
    try {
      const stocks = await stockAPI.getStocks(date);
      set({ stocks, loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '載入股票清單失敗',
        loading: false
      });
    }
  },

  // 載入股票資料
  loadStockData: async (date: string, stockCode: string) => {
    set({ loading: true, error: null });
    try {
      const stockData = await stockAPI.getStockData(date, stockCode);

      // 建立統一時間軸（合併成交和五檔的所有時間點）
      const unifiedTimestamps = new Set<string>();

      // 添加成交時間
      if (stockData.chart?.timestamps) {
        stockData.chart.timestamps.forEach(t => unifiedTimestamps.add(t));
      }

      // 添加五檔時間
      if (stockData.depth_history) {
        stockData.depth_history.forEach(d => unifiedTimestamps.add(d.timestamp));
      }

      // 排序並存儲統一時間軸
      let sortedTimestamps = Array.from(unifiedTimestamps).sort();

      // 效能優化：自動過濾
      const currentInterval = get().timelineInterval;
      if (sortedTimestamps.length > 50000 && currentInterval === 0) {
        // 自動啟用 100ms 間隔過濾以提升渲染效能
        set({ timelineInterval: 100 });
      }

      // 應用時間間隔過濾
      const intervalMs = get().timelineInterval;
      if (intervalMs > 0) {
        const filtered = [sortedTimestamps[0]];
        let lastTime = new Date(sortedTimestamps[0]).getTime();

        for (const timestamp of sortedTimestamps) {
          const currentTime = new Date(timestamp).getTime();
          if (currentTime - lastTime >= intervalMs) {
            filtered.push(timestamp);
            lastTime = currentTime;
          }
        }

        // 確保最後一個時間點被包含
        if (filtered[filtered.length - 1] !== sortedTimestamps[sortedTimestamps.length - 1]) {
          filtered.push(sortedTimestamps[sortedTimestamps.length - 1]);
        }

        sortedTimestamps = filtered;
      }

      // 將統一時間軸附加到 stockData
      const enrichedStockData = {
        ...stockData,
        unifiedTimeline: sortedTimestamps
      };

      set({ stockData: enrichedStockData, loading: false, currentTimeIndex: 0 });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '載入股票資料失敗',
        loading: false
      });
    }
  },

  // 設定選中的日期
  setSelectedDate: (date) => {
    set({ selectedDate: date, selectedStock: null, stockData: null });
    if (date) {
      get().loadStocks(date);
    }
  },

  // 設定選中的股票
  setSelectedStock: (stock) => {
    set({ selectedStock: stock });
    const { selectedDate } = get();
    if (selectedDate && stock) {
      get().loadStockData(selectedDate, stock);
    }
  },

  // 切換播放狀態
  togglePlayback: () => {
    set((state) => ({ isPlaying: !state.isPlaying }));
  },

  // 設定播放速度
  setPlaybackSpeed: (speed) => {
    set({ playbackSpeed: speed });
  },

  // 設定當前時間索引
  setCurrentTimeIndex: (index) => {
    set({ currentTimeIndex: index });
  },

  // 切換縮放模式
  toggleZoomMode: () => {
    set((state) => ({
      zoomMode: state.zoomMode === 'dynamic' ? 'full' : 'dynamic'
    }));
  },
}));
