import axios from 'axios';
import type { StockData } from '@/types/stock';

// 設定 API 基礎 URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 股票 API 服務
 */
export const stockAPI = {
  /**
   * 取得所有可用日期
   */
  async getDates(): Promise<string[]> {
    const response = await api.get<string[]>('/api/dates');
    return response.data;
  },

  /**
   * 取得指定日期的股票清單
   */
  async getStocks(date: string): Promise<string[]> {
    const response = await api.get<string[]>(`/api/stocks/${date}`);
    return response.data;
  },

  /**
   * 取得股票完整資料
   */
  async getStockData(date: string, stockCode: string): Promise<StockData> {
    const response = await api.get<StockData>(`/api/data/${date}/${stockCode}`);
    return response.data;
  },
};

export default api;
