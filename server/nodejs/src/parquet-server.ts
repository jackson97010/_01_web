import express, { Request, Response } from 'express';
import cors from 'cors';
import compression from 'compression';
import path from 'path';
import fs from 'fs/promises';
import { existsSync } from 'fs';
import { readParquet } from 'parquet-wasm';

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(compression());
app.use(express.json());

// Paths
const frontendBuildPath = path.join(__dirname, '../../../frontend-app/dist');
const decodedDataPath = path.join(__dirname, '../../../data/decoded_quotes');

// Log startup info
console.log('🚀 Stock Quote Playback API Server (Parquet Direct)');
console.log('📁 Decoded Data Path:', decodedDataPath);
console.log('📁 Frontend Build Path:', frontendBuildPath);

// Helper: Determine inner/outer
function determineInnerOuter(
  currentPrice: number,
  prevBid1: number | null,
  prevAsk1: number | null
): string {
  if (prevAsk1 !== null && currentPrice >= prevAsk1) {
    return '外';
  } else if (prevBid1 !== null && currentPrice <= prevBid1) {
    return '內';
  } else {
    return '–';
  }
}

// Helper: Convert Parquet to JSON format
async function convertParquetToJson(parquetPath: string): Promise<any> {
  try {
    // Read parquet file
    const buffer = await fs.readFile(parquetPath);
    const uint8Array = new Uint8Array(buffer);
    const table = readParquet(uint8Array);

    // Convert to array of objects
    const data: any[] = [];
    const numRows = table.numRows;

    // Get column names
    const schema = table.schema;
    const fieldNames = schema.fields.map((f: any) => f.name);

    // Read all rows
    for (let i = 0; i < numRows; i++) {
      const row: any = {};
      for (const fieldName of fieldNames) {
        const column = table.getChild(fieldName);
        row[fieldName] = column?.get(i);
      }
      data.push(row);
    }

    if (data.length === 0) {
      return null;
    }

    // Separate Trade and Depth
    const trades = data.filter((row) => row.Type === 'Trade');
    const depths = data.filter((row) => row.Type === 'Depth');

    const stockCode = data[0].StockCode;
    const dateStr = new Date(data[0].Datetime).toISOString().slice(0, 10).replace(/-/g, '');

    // Process trades
    const tradesJson: any[] = [];
    if (trades.length > 0) {
      // Sort by datetime descending
      trades.sort((a, b) => new Date(b.Datetime).getTime() - new Date(a.Datetime).getTime());

      let prevBid1: number | null = null;
      let prevAsk1: number | null = null;

      for (const trade of trades) {
        // Find previous depth before this trade
        const prevDepth = depths
          .filter((d) => new Date(d.Datetime) < new Date(trade.Datetime))
          .sort((a, b) => new Date(b.Datetime).getTime() - new Date(a.Datetime).getTime())[0];

        if (prevDepth) {
          prevBid1 = prevDepth.Bid1_Price || null;
          prevAsk1 = prevDepth.Ask1_Price || null;
        }

        const innerOuter = determineInnerOuter(trade.Price, prevBid1, prevAsk1);

        tradesJson.push({
          time: new Date(trade.Datetime).toISOString().replace('T', ' ').replace('Z', ''),
          price: trade.Price,
          volume: trade.Volume,
          inner_outer: innerOuter,
          flag: trade.Flag,
        });
      }
    }

    // Process depth_history
    const depthHistory: any[] = [];
    if (depths.length > 0) {
      depths.sort((a, b) => new Date(a.Datetime).getTime() - new Date(b.Datetime).getTime());

      for (const depth of depths) {
        const bids: any[] = [];
        const asks: any[] = [];

        // Extract bids
        for (let i = 1; i <= 5; i++) {
          const bidPrice = depth[`Bid${i}_Price`];
          const bidVolume = depth[`Bid${i}_Volume`];
          if (bidPrice != null && bidVolume != null) {
            bids.push({ price: bidPrice, volume: bidVolume });
          }
        }

        // Extract asks
        for (let i = 1; i <= 5; i++) {
          const askPrice = depth[`Ask${i}_Price`];
          const askVolume = depth[`Ask${i}_Volume`];
          if (askPrice != null && askVolume != null) {
            asks.push({ price: askPrice, volume: askVolume });
          }
        }

        depthHistory.push({
          timestamp: new Date(depth.Datetime).toISOString().replace('T', ' ').replace('Z', ''),
          bids,
          asks,
        });
      }
    }

    // Current depth (latest)
    const depth = depthHistory.length > 0 ? {
      bids: depthHistory[depthHistory.length - 1].bids,
      asks: depthHistory[depthHistory.length - 1].asks,
      timestamp: depthHistory[depthHistory.length - 1].timestamp,
    } : null;

    // Process chart
    let chart = null;
    if (trades.length > 0) {
      const tradesSorted = [...trades].sort(
        (a, b) => new Date(a.Datetime).getTime() - new Date(b.Datetime).getTime()
      );

      const timestamps = tradesSorted.map((t) =>
        new Date(t.Datetime).toISOString().replace('T', ' ').replace('Z', '')
      );
      const prices = tradesSorted.map((t) => t.Price);
      const volumes = tradesSorted.map((t) => t.Volume);

      // Cumulative volumes
      const totalVolumes: number[] = [];
      let cumVol = 0;
      for (const vol of volumes) {
        cumVol += vol;
        totalVolumes.push(cumVol);
      }

      // VWAP
      const vwap: number[] = [];
      let cumAmount = 0;
      let cumVolume = 0;
      for (let i = 0; i < tradesSorted.length; i++) {
        cumAmount += tradesSorted[i].Price * tradesSorted[i].Volume;
        cumVolume += tradesSorted[i].Volume;
        vwap.push(cumVolume > 0 ? cumAmount / cumVolume : 0);
      }

      chart = {
        timestamps,
        prices,
        volumes,
        total_volumes: totalVolumes,
        vwap,
      };
    }

    // Process stats
    let stats = null;
    if (trades.length > 0) {
      const tradesSorted = [...trades].sort(
        (a, b) => new Date(a.Datetime).getTime() - new Date(b.Datetime).getTime()
      );

      const openPrice = tradesSorted[0].Price;
      const currentPrice = tradesSorted[tradesSorted.length - 1].Price;
      const highPrice = Math.max(...tradesSorted.map((t) => t.Price));
      const lowPrice = Math.min(...tradesSorted.map((t) => t.Price));

      const totalAmount = tradesSorted.reduce((sum, t) => sum + t.Price * t.Volume, 0);
      const totalVolume = tradesSorted.reduce((sum, t) => sum + t.Volume, 0);
      const avgPrice = totalVolume > 0 ? totalAmount / totalVolume : 0;

      const tradeCount = tradesSorted.length;
      const change = currentPrice - openPrice;
      const changePct = openPrice > 0 ? (change / openPrice) * 100 : 0;

      stats = {
        current_price: currentPrice,
        open_price: openPrice,
        high_price: highPrice,
        low_price: lowPrice,
        avg_price: avgPrice,
        total_volume: totalVolume,
        trade_count: tradeCount,
        change,
        change_pct: changePct,
      };
    }

    return {
      chart,
      depth,
      depth_history: depthHistory,
      trades: tradesJson,
      stats,
      stock_code: stockCode,
      date: dateStr,
    };
  } catch (error) {
    console.error('Error converting parquet:', error);
    return null;
  }
}

// API Routes

/**
 * GET /api/dates
 * Returns list of available dates
 */
app.get('/api/dates', async (req: Request, res: Response) => {
  try {
    const entries = await fs.readdir(decodedDataPath, { withFileTypes: true });
    const dates = entries
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .filter((name) => /^\d{8}$/.test(name)) // YYYYMMDD format
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
    const datePath = path.join(decodedDataPath, date);

    const files = await fs.readdir(datePath);
    const stocks = files
      .filter((file) => file.endsWith('.parquet'))
      .map((file) => file.replace('.parquet', ''))
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
    const filePath = path.join(decodedDataPath, date, `${stock}.parquet`);

    if (!existsSync(filePath)) {
      res.status(404).json({ error: 'Stock data not found' });
      return;
    }

    // Convert parquet to JSON on-the-fly
    const data = await convertParquetToJson(filePath);

    if (data) {
      res.json(data);
    } else {
      res.status(500).json({ error: 'Failed to convert data' });
    }
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

// Start server
app.listen(PORT, () => {
  console.log(`✅ Server running on http://localhost:${PORT}`);
  console.log(`📊 API available at http://localhost:${PORT}/api`);
  console.log('');
  console.log('Available endpoints:');
  console.log(`  GET /api/dates - List all available dates`);
  console.log(`  GET /api/stocks/:date - List stocks for a date`);
  console.log(`  GET /api/data/:date/:stock - Get stock data`);
});
