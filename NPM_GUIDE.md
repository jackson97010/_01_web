# NPM 前後端使用指南

## 目前狀態分析

您的專案已經配置好了完整的 npm 前後端架構：

### 前端 (frontend-app)
- ✅ React + TypeScript + Vite
- ✅ 開發 server: port 3000
- ✅ API proxy 已設定（自動轉發 /api 到 localhost:5000）
- ✅ Tailwind CSS
- ✅ Chart.js + Zustand
- ✅ **無需修改**，配置已經正確！

### 後端 (server/nodejs)
- ✅ Express + TypeScript
- ✅ API 端點正確（/api/dates, /api/stocks, /api/data）
- ✅ CORS 已啟用
- ✅ Compression 已啟用
- ✅ **只需要資料目錄正確即可使用**

---

## 快速開始

### 方案 1：使用預先轉換的 JSON（最簡單）⭐

**步驟 1：轉換資料**
```bash
cd C:\Users\User\Documents\_web\_01_web
python scripts\convert_to_json.py
```
這會將 Parquet 檔案轉換為 JSON，存放在 `frontend/static/api/`

**步驟 2：啟動後端**
```bash
cd server\nodejs
npm install
npm run dev
```
後端會在 http://localhost:5000 啟動

**步驟 3：啟動前端**（開新的終端機）
```bash
cd frontend-app
npm install
npm run dev
```
前端會在 http://localhost:3000 啟動

**步驟 4：開啟瀏覽器**
```
http://localhost:3000
```

---

### 方案 2：使用 Python Parquet Server + React 前端

如果您想節省空間，不轉換為 JSON：

**步驟 1：啟動 Python Parquet Server**
```bash
cd server\python
python parquet_server.py --port 5000
```

**步驟 2：啟動前端**（開新的終端機）
```bash
cd frontend-app
npm install
npm run dev
```

**步驟 3：開啟瀏覽器**
```
http://localhost:3000
```

---

## 詳細說明

### 前端 (frontend-app)

#### 安裝依賴
```bash
cd frontend-app
npm install
```

#### 開發模式（推薦）
```bash
npm run dev
```
- 啟動 Vite 開發 server (http://localhost:3000)
- 支援熱更新（Hot Module Replacement）
- 自動 proxy API 請求到 localhost:5000

#### 打包生產版本
```bash
npm run build
```
- 輸出到 `dist/` 目錄
- 優化和壓縮程式碼
- 生成 source map（可選）

#### 預覽生產版本
```bash
npm run preview
```
- 預覽打包後的結果

#### 環境變數設定（可選）

創建 `.env` 檔案在 `frontend-app/` 目錄：
```env
# API 基礎 URL（開發模式會自動 proxy）
VITE_API_URL=http://localhost:5000
```

### 後端 (server/nodejs)

#### 安裝依賴
```bash
cd server\nodejs
npm install
```

#### 開發模式（自動重啟）
```bash
npm run dev
```
- 使用 `tsx watch` 監控檔案變化
- 自動重新啟動
- 適合開發時使用

#### 打包（編譯 TypeScript）
```bash
npm run build
```
- 編譯 TypeScript 到 JavaScript
- 輸出到 `dist/` 目錄

#### 生產模式
```bash
npm run build
npm start
```
- 先編譯，再啟動
- 使用編譯後的 JavaScript

#### 清理編譯結果
```bash
npm run clean
```

---

## 完整的開發流程

### 首次設定

**1. 確保資料已解碼**
```bash
cd C:\Users\User\Documents\_web\_01_web
python scripts\batch_decode_quotes.py
```

**2. 選擇資料來源**

**選項 A：轉換為 JSON**
```bash
python scripts\convert_to_json.py
```

**選項 B：使用 Parquet Server**（跳過此步驟）

**3. 安裝所有依賴**
```bash
# 前端
cd frontend-app
npm install

# 後端
cd ..\server\nodejs
npm install
```

### 日常開發

**開啟 3 個終端機視窗：**

**終端機 1：後端**
```bash
cd server\nodejs
npm run dev
```

**終端機 2：前端**
```bash
cd frontend-app
npm run dev
```

**終端機 3：資料處理**（需要時）
```bash
# 解碼新資料
python scripts\batch_decode_quotes.py

# 轉換為 JSON（如果使用選項 A）
python scripts\convert_to_json.py
```

---

## 配置說明

### frontend-app 配置

#### vite.config.ts
```typescript
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',  // 後端位置
        changeOrigin: true,
      },
    },
  },
})
```
✅ **無需修改**，配置已正確

#### API 服務 (src/services/api.ts)
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
```
✅ **無需修改**，自動讀取環境變數

### 後端配置

#### server/nodejs/src/server.ts
```typescript
const apiDataPath = path.join(__dirname, '../../../frontend/static/api');
```
✅ **無需修改**，路徑已正確指向 JSON 資料

---

## API 端點說明

前端會自動調用這些 API（透過 proxy）：

```
開發模式：
前端：http://localhost:3000
後端：http://localhost:5000

API 調用：
http://localhost:3000/api/dates
  → 自動 proxy 到 →
http://localhost:5000/api/dates
```

### 可用的 API

```http
GET /api/dates
回應: ["20251031", "20251103", ...]

GET /api/stocks/:date
回應: ["1503", "1514", "1519", ...]

GET /api/data/:date/:stock
回應: { chart, depth, trades, stats, ... }
```

---

## 生產部署

### 打包前端
```bash
cd frontend-app
npm run build
```

### 打包後端
```bash
cd server\nodejs
npm run build
```

### 部署方式

**方式 1：使用 Node.js Server**
```bash
# 1. 打包前端
cd frontend-app
npm run build

# 2. 複製前端到後端
cp -r dist ../server/nodejs/frontend-dist

# 3. 修改後端提供靜態檔案
# 在 server.ts 中添加：
app.use(express.static('frontend-dist'));

# 4. 啟動
cd ../server/nodejs
npm run build
npm start
```

**方式 2：分別部署**
- 前端：部署到 Vercel / Netlify / GitHub Pages
- 後端：部署到 Heroku / Railway / VPS
- 記得設定 CORS 和環境變數

---

## 故障排除

### 問題 1：前端無法連接後端

**檢查**：
```bash
# 確認後端正在運行
curl http://localhost:5000/api/dates
```

**解決**：
1. 確認後端已啟動（npm run dev）
2. 確認 port 5000 沒有被佔用
3. 檢查防火牆設定

### 問題 2：API 返回 404

**檢查**：
```bash
# 確認資料目錄存在
ls frontend\static\api
```

**解決**：
```bash
# 轉換資料
python scripts\convert_to_json.py
```

### 問題 3：前端打包錯誤

**檢查**：
```bash
# 檢查 TypeScript 錯誤
cd frontend-app
npx tsc --noEmit
```

**解決**：
1. 修正 TypeScript 錯誤
2. 確認所有依賴已安裝
3. 刪除 node_modules 重新安裝

### 問題 4：熱更新不工作

**解決**：
```bash
# 重啟前端 dev server
cd frontend-app
npm run dev
```

---

## 效能優化建議

### 前端優化

**1. 程式碼分割（已配置）**
```typescript
// vite.config.ts
manualChunks: {
  'react-vendor': ['react', 'react-dom'],
  'chart-vendor': ['chart.js', 'react-chartjs-2'],
}
```

**2. 圖片優化**
- 使用 WebP 格式
- 添加 lazy loading

**3. API 快取**
```typescript
// 在 api.ts 中添加快取
const cache = new Map();

async getDates(): Promise<string[]> {
  if (cache.has('dates')) {
    return cache.get('dates');
  }
  const data = await api.get('/api/dates');
  cache.set('dates', data);
  return data;
}
```

### 後端優化

**1. 添加快取**
```typescript
import NodeCache from 'node-cache';
const cache = new NodeCache({ stdTTL: 3600 });
```

**2. 壓縮（已配置）**
```typescript
app.use(compression());
```

**3. 添加 Rate Limiting**
```bash
npm install express-rate-limit
```

---

## 開發工具推薦

### VS Code 擴充功能

**前端開發**：
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- TypeScript Vue Plugin (Volar)

**後端開發**：
- REST Client
- Thunder Client（測試 API）

### 瀏覽器工具

- React Developer Tools
- Redux DevTools（如果使用）
- Network 面板（查看 API 請求）

---

## NPM Scripts 總覽

### frontend-app
```json
{
  "dev": "vite",              // 開發模式
  "build": "tsc && vite build", // 打包
  "preview": "vite preview"   // 預覽打包結果
}
```

### server/nodejs
```json
{
  "dev": "tsx watch src/server.ts",  // 開發模式（自動重啟）
  "build": "tsc",                    // 編譯 TypeScript
  "start": "node dist/server.js",    // 生產模式
  "clean": "rimraf dist"             // 清理編譯結果
}
```

---

## 常用命令速查

```bash
# === 前端 ===
cd frontend-app

# 安裝依賴
npm install

# 開發
npm run dev          # http://localhost:3000

# 打包
npm run build        # 輸出到 dist/

# 預覽
npm run preview


# === 後端 ===
cd server\nodejs

# 安裝依賴
npm install

# 開發（自動重啟）
npm run dev          # http://localhost:5000

# 打包
npm run build

# 生產
npm start


# === 資料處理 ===
cd C:\Users\User\Documents\_web\_01_web

# 解碼 Parquet
python scripts\batch_decode_quotes.py

# 轉換為 JSON
python scripts\convert_to_json.py

# 驗證資料
python scripts\verify_decode.py
```

---

## 結論

✅ **您的前後端配置已經完全正確，無需修改！**

**推薦的開發流程**：

1. **首次設定**：
   ```bash
   # 轉換資料
   python scripts\convert_to_json.py

   # 安裝依賴
   cd frontend-app && npm install
   cd ..\server\nodejs && npm install
   ```

2. **日常開發**：
   ```bash
   # 終端機 1：後端
   cd server\nodejs && npm run dev

   # 終端機 2：前端
   cd frontend-app && npm run dev
   ```

3. **開啟瀏覽器**：
   ```
   http://localhost:3000
   ```

就這麼簡單！🚀

---

**文件更新日期**：2025-11-20
**版本**：1.0
