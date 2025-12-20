import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 載入 Rust 模塊（暫時禁用以診斷問題）
let nativeModule = null;
const USE_RUST = false; // 設為 false 暫時禁用 Rust，設為 true 啟用
if (USE_RUST) {
  try {
    nativeModule = require('../native/index.node');
    console.log('✅ Rust 模塊載入成功');
  } catch (error) {
    console.warn('⚠️  Rust 模塊未找到，將使用 JavaScript 版本:', error.message);
  }
} else {
  console.log('ℹ️ Rust 模塊已手動禁用，使用 JavaScript 版本');
}

const isDev = process.env.NODE_ENV === 'development';
const devServerUrl = process.env.VITE_DEV_SERVER_URL || 'http://localhost:5173';

let mainWindow = null;

async function readParquet(filePath) {
  const parquet = await import('parquetjs-lite');
  const reader = await parquet.ParquetReader.openFile(filePath);
  const cursor = reader.getCursor();
  const rows = [];
  let record;
  // parquetjs-lite returns plain JS objects
  // eslint-disable-next-line no-cond-assign
  while ((record = await cursor.next())) {
    rows.push(record);
  }
  await reader.close();
  return rows;
}

async function loadFile(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.json') {
    let raw = fs.readFileSync(filePath, 'utf-8');
    // 處理 NaN, Infinity 等非標準 JSON 值
    raw = raw.replace(/:\s*NaN\s*([,\}])/g, ': null$1');
    raw = raw.replace(/:\s*Infinity\s*([,\}])/g, ': null$1');
    raw = raw.replace(/:\s*-Infinity\s*([,\}])/g, ': null$1');

    const data = JSON.parse(raw);

    // 🚀 使用 Rust 處理數據（如果可用）
    if (nativeModule && nativeModule.processReplayDataJson) {
      try {
        console.time('Rust processing');
        const processedJson = nativeModule.processReplayDataJson(JSON.stringify(data));
        const processed = JSON.parse(processedJson);
        console.timeEnd('Rust processing');
        console.log(`✅ Rust 處理完成: ${processed.length} 筆數據`);
        return processed;
      } catch (error) {
        console.warn('⚠️  Rust 處理失敗，使用 JavaScript 版本:', error.message);
        return data;
      }
    }

    return data;
  }

  if (ext === '.parquet') {
    const rows = await readParquet(filePath);

    // 🚀 使用 Rust 處理數據（如果可用）
    if (nativeModule && nativeModule.processReplayDataJson) {
      try {
        console.time('Rust processing');
        const processedJson = nativeModule.processReplayDataJson(JSON.stringify(rows));
        const processed = JSON.parse(processedJson);
        console.timeEnd('Rust processing');
        console.log(`✅ Rust 處理完成: ${processed.length} 筆數據`);
        return processed;
      } catch (error) {
        console.warn('⚠️  Rust 處理失敗，使用原始數據:', error.message);
        return rows;
      }
    }

    return rows;
  }

  throw new Error(`Unsupported file type: ${ext}`);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  if (isDev) {
    mainWindow.loadURL(devServerUrl);
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
    // 暫時開啟開發者工具以查看錯誤
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  ipcMain.handle('dialog:openFile', async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: [
        { name: 'Data', extensions: ['json', 'parquet'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    });
    if (canceled || filePaths.length === 0) return null;
    return filePaths[0];
  });

  ipcMain.handle('file:load', async (_evt, filePath) => {
    return loadFile(filePath);
  });

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
