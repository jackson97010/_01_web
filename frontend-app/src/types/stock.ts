// 圖表資料型別
export interface ChartData {
  timestamps: string[];
  prices: number[];
  volumes: number[];
  total_volumes: number[];
  vwap: number[];
}

// 五檔報價型別
export interface PriceLevel {
  price: number;
  volume: number;
}

export interface DepthData {
  bids: PriceLevel[];
  asks: PriceLevel[];
  timestamp: string;
}

// 五檔歷史型別
export interface DepthHistory {
  timestamp: string;
  bids: PriceLevel[];
  asks: PriceLevel[];
}

// 成交明細型別
export interface Trade {
  time: string;
  price: number;
  volume: number;
  inner_outer: '內盤' | '外盤' | '–';
  flag: number;
}

// 統計資料型別
export interface Statistics {
  current_price: number;
  open_price: number;
  high_price: number;
  low_price: number;
  avg_price: number;
  total_volume: number;
  trade_count: number;
  change: number;
  change_pct: number;
}

// 完整股票資料型別
export interface StockData {
  chart: ChartData | null;
  depth: DepthData | null;
  depth_history: DepthHistory[];
  trades: Trade[];
  stats: Statistics | null;
  stock_code: string;
  date: string;
  unifiedTimeline?: string[]; // 統一時間軸（合併成交和五檔）
}

// API 回應型別
export interface ApiError {
  error: string;
}
