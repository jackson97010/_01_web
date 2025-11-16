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
