import express, { Request, Response } from 'express';
import cors from 'cors';
import compression from 'compression';
import path from 'path';
import fs from 'fs/promises';

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(compression());
app.use(express.json());

// Static file serving - frontend build
const frontendBuildPath = path.join(__dirname, '../../../frontend-app/dist');
const apiDataPath = path.join(__dirname, '../../../frontend/static/api');

// Log startup info
console.log('🚀 Stock Quote Playback API Server');
console.log('📁 API Data Path:', apiDataPath);
console.log('📁 Frontend Build Path:', frontendBuildPath);

// API Routes

/**
 * GET /api/dates
 * Returns list of available dates
 */
app.get('/api/dates', async (req: Request, res: Response) => {
  try {
    const entries = await fs.readdir(apiDataPath, { withFileTypes: true });
    const dates = entries
      .filter(entry => entry.isDirectory())
      .map(entry => entry.name)
      .filter(name => /^\d{8}$/.test(name)) // YYYYMMDD format
      .sort()
      .reverse(); // Latest first

    res.json(dates);
  } catch (error) {
    console.error('Error reading dates:', error);
    res.status(500).json({ error: 'Failed to read dates' });
  }
});

/**
 * GET /api/stocks/:date
 * Returns list of available stocks for a specific date
 */
app.get('/api/stocks/:date', async (req: Request, res: Response) => {
  try {
    const { date } = req.params;
    const datePath = path.join(apiDataPath, date);

    const files = await fs.readdir(datePath);
    const stocks = files
      .filter(file => file.endsWith('.json'))
      .map(file => file.replace('.json', ''))
      .sort();

    res.json(stocks);
  } catch (error) {
    console.error(`Error reading stocks for date ${req.params.date}:`, error);
    res.status(500).json({ error: 'Failed to read stocks' });
  }
});

/**
 * GET /api/data/:date/:stock
 * Returns stock data for a specific date and stock code
 */
app.get('/api/data/:date/:stock', async (req: Request, res: Response) => {
  try {
    const { date, stock } = req.params;
    const filePath = path.join(apiDataPath, date, `${stock}.json`);

    const fileContent = await fs.readFile(filePath, 'utf-8');
    const data = JSON.parse(fileContent);

    // 過濾掉試撮資料（flag=1，09:00 以前的交易）
    // 只保留 09:00:00 之後的資料
    const filterTime = (timeStr: string) => {
      // 提取時間部分 "HH:MM:SS"
      const timePart = timeStr.split(' ')[1];
      if (!timePart) return false;
      const hour = parseInt(timePart.split(':')[0]);
      return hour >= 9;
    };

    // 過濾 trades
    if (data.trades && Array.isArray(data.trades)) {
      // 只過濾掉 09:00 以前的交易，保留 FLAG=0 和 FLAG=1 的交易
      data.trades = data.trades.filter((trade: any) => filterTime(trade.time));

      // 重新計算累積總量（trades 是倒序的，所以需要反向計算）
      // 只計算 FLAG=0 的正式交易量
      let cumulativeVolume = 0;
      for (let i = data.trades.length - 1; i >= 0; i--) {
        if (data.trades[i].flag === 0) {
          cumulativeVolume += data.trades[i].volume;
        }
        data.trades[i].total_volume = cumulativeVolume;
      }
    }

    // 處理圖表資料（chart 是正序的，從舊到新）
    if (data.chart && data.chart.timestamps) {
      const validIndices: number[] = [];
      data.chart.timestamps.forEach((timestamp: string, index: number) => {
        // 只保留 09:00 之後的資料（包含 FLAG=0 和 FLAG=1）
        if (filterTime(timestamp)) {
          validIndices.push(index);
        }
      });

      if (validIndices.length > 0) {
        data.chart.timestamps = validIndices.map(i => data.chart.timestamps[i]);
        data.chart.prices = validIndices.map(i => data.chart.prices[i]);
        data.chart.volumes = validIndices.map(i => data.chart.volumes[i]);
        data.chart.flags = validIndices.map(i => data.chart.flags?.[i] ?? 0);

        // 處理緩搓期間的價格：使用最後一個正式交易（flag=0）的價格
        let lastFormalPrice = data.chart.prices[0]; // 初始價格
        for (let i = 0; i < data.chart.prices.length; i++) {
          const flag = data.chart.flags[i];
          if (flag === 0) {
            // 正式交易，更新最後價格
            lastFormalPrice = data.chart.prices[i];
          } else {
            // 緩搓期間，使用最後的正式交易價格
            data.chart.prices[i] = lastFormalPrice;
          }
        }

        // 重新計算累積量（只計算 flag=0 的成交量）
        let cumsum = 0;
        data.chart.total_volumes = data.chart.volumes.map((v: number, i: number) => {
          if (data.chart.flags[i] === 0) {
            cumsum += v;
          }
          return cumsum;
        });

        // 重新計算 VWAP（只使用 flag=0 的資料）
        let cumulativeAmount = 0;
        let cumulativeVolume = 0;
        data.chart.vwap = data.chart.prices.map((price: number, i: number) => {
          const flag = data.chart.flags[i];
          if (flag === 0) {
            const volume = data.chart.volumes[i];
            cumulativeAmount += price * volume;
            cumulativeVolume += volume;
          }
          return cumulativeVolume > 0 ? cumulativeAmount / cumulativeVolume : 0;
        });
      } else {
        // 如果沒有有效資料，清空圖表
        data.chart = null;
      }
    }

    // 重新計算統計數據（基於過濾後的交易，只計算 FLAG=0 的正式交易）
    if (data.stats && data.trades && data.trades.length > 0) {
      // 只使用 FLAG=0 的正式交易來計算統計數據
      const formalTrades = data.trades.filter((t: any) => t.flag === 0);

      if (formalTrades.length > 0) {
        const prices = formalTrades.map((t: any) => t.price);
        const volumes = formalTrades.map((t: any) => t.volume);

        data.stats.open_price = prices[prices.length - 1]; // 最舊的（reversed）
        data.stats.current_price = prices[0]; // 最新的
        data.stats.high_price = Math.max(...prices);
        data.stats.low_price = Math.min(...prices);

        const totalAmount = formalTrades.reduce((sum: number, t: any) => sum + t.price * t.volume, 0);
        const totalVolume = volumes.reduce((sum: number, v: number) => sum + v, 0);
        data.stats.avg_price = totalVolume > 0 ? totalAmount / totalVolume : 0;
        data.stats.total_volume = totalVolume;
        data.stats.trade_count = formalTrades.length;

        data.stats.change = data.stats.current_price - data.stats.open_price;
        data.stats.change_pct = data.stats.open_price > 0
          ? (data.stats.change / data.stats.open_price) * 100
          : 0;
      }
    }

    res.json(data);
  } catch (error) {
    console.error(`Error reading data for ${req.params.date}/${req.params.stock}:`, error);
    res.status(404).json({ error: 'Stock data not found' });
  }
});

// Serve frontend static files (production mode)
app.use(express.static(frontendBuildPath));

// SPA fallback - all other routes return index.html
app.get('*', async (req: Request, res: Response) => {
  try {
    const indexPath = path.join(frontendBuildPath, 'index.html');
    res.sendFile(indexPath);
  } catch (error) {
    res.status(404).send('Frontend not built. Run `npm run build` in frontend-app directory.');
  }
});

// Start server with error handling
const server = app.listen(PORT, () => {
  console.log(`✅ Server running on http://localhost:${PORT}`);
  console.log(`📊 API available at http://localhost:${PORT}/api`);
  console.log('');
  console.log('Available endpoints:');
  console.log(`  GET /api/dates - List all available dates`);
  console.log(`  GET /api/stocks/:date - List stocks for a date`);
  console.log(`  GET /api/data/:date/:stock - Get stock data`);
});

// Handle port in use error
server.on('error', (error: NodeJS.ErrnoException) => {
  if (error.code === 'EADDRINUSE') {
    console.error(`❌ Error: Port ${PORT} is already in use.`);
    console.error('');
    console.error('Solutions:');
    console.error('  1. Kill the process using the port:');
    console.error(`     Windows: netstat -ano | findstr :${PORT}`);
    console.error(`              taskkill /F /PID <PID>`);
    console.error('');
    console.error('  2. Use a different port:');
    console.error('     set PORT=3000 && npm start');
    console.error('');
    process.exit(1);
  } else {
    console.error('❌ Server error:', error);
    process.exit(1);
  }
});
