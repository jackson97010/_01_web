# 台股即時報價回放系統

一個高效能的台股歷史報價視覺化與回放系統，支援分tick級別的五檔報價與成交明細時間軸回放。

[![React](https://img.shields.io/badge/React-18-blue)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ⚡ 特色功能

### 核心功能
- 📊 **價格走勢圖** - Chart.js 圖表，含 VWAP 指標與紅點定位
- 📈 **每分鐘累積成交量** - 前端即時計算，無需後端處理
- 💹 **五檔報價** - 即時買賣五檔報價，視覺化價量柱狀圖
- 📋 **成交明細** - 完整的 tick-by-tick 成交記錄，含內外盤判斷
- ⏱️ **統一時間軸回放** - 完整重現五檔與成交的所有變化
- 🎯 **毫秒級精度** - 所有時間戳精確到毫秒（HH:MM:SS.mmm）

### 技術亮點
- 🔄 **統一時間軸架構** - 合併成交與五檔時間點，五檔可獨立更新
- ⚡ **智能效能優化** - 超過50000時間點自動啟用100ms間隔過濾
- 🎬 **無動畫渲染** - Chart.js 動畫已停用，確保流暢播放
- 💾 **前端狀態管理** - Zustand 輕量化狀態管理
- 🎨 **現代化 UI** - TailwindCSS + 深色模式支援

---

## 📂 專案結構

```
_01_web/
├── README.md                      # 本文件
├── .gitignore                     # Git 忽略檔案（已排除大型資料）
│
├── frontend-app/                  # React + TypeScript 前端應用 ⭐ 新版
│   ├── src/
│   │   ├── components/            # React 組件
│   │   │   ├── Header.tsx         # 頂部導航與選單
│   │   │   ├── StockChart.tsx     # 價格與成交量圖表
│   │   │   ├── DepthTable.tsx     # 五檔報價表
│   │   │   ├── TradeList.tsx      # 成交明細列表
│   │   │   └── TimelineControls.tsx # 時間軸控制器
│   │   │
│   │   ├── stores/                # Zustand 狀態管理
│   │   │   └── stockStore.ts      # 全域狀態（含統一時間軸）
│   │   │
│   │   ├── services/              # API 服務
│   │   │   └── api.ts             # HTTP 請求封裝
│   │   │
│   │   ├── types/                 # TypeScript 型別定義
│   │   │   └── stock.ts           # 資料型別
│   │   │
│   │   └── styles/                # 樣式檔案
│   │       └── index.css          # TailwindCSS
│   │
│   ├── package.json               # 依賴管理
│   ├── vite.config.ts             # Vite 設定
│   └── tsconfig.json              # TypeScript 設定
│
├── server/                        # 後端伺服器
│   ├── nodejs/                    # Node.js/TypeScript 伺服器 ⭐ 推薦
│   │   ├── src/server.ts          # Express.js 主程式
│   │   ├── package.json           # 依賴管理
│   │   └── tsconfig.json          # TypeScript 設定
│   └── python/                    # Python 靜態檔案伺服器（備用）
│       └── static_server.py       # HTTP server (CORS enabled)
│
├── scripts/                       # 資料處理腳本
│   └── preprocess.py              # Parquet → JSON 預處理
│
├── frontend/static/api/           # 處理後的 JSON 資料
│   └── [YYYYMMDD]/                # 日期資料夾
│       └── [股票代碼].json
│
├── data/                          # 原始資料（不上傳 GitHub）
│   └── processed_data/            # Parquet 檔案
│
└── docs/                          # 文件與截圖
    ├── UNIFIED_TIMELINE_IMPLEMENTATION.md  # 統一時間軸說明
    └── screenshots/
```

---

## 🚀 快速開始

### 前置需求

- **Node.js 18+**
- **npm** 或 **yarn**
- **Python 3.8+**（用於資料處理）

### 方式 1：使用啟動腳本（最簡單）⭐

**Windows 用戶**：
```bash
# 雙擊執行（使用 Node.js 後端）
start-dev.bat

# 或使用 Python Parquet Server（節省空間）
start-parquet.bat
```

腳本會自動：
1. 轉換資料（如果需要）
2. 啟動後端 (http://localhost:5000)
3. 啟動前端 (http://localhost:3000)
4. 開啟瀏覽器

### 方式 2：手動啟動

**首次設定**：

1. **Clone 專案**
```bash
git clone https://github.com/your-username/_01_web.git
cd _01_web
```

2. **安裝依賴**
```bash
# 前端
cd frontend-app
npm install

# 後端
cd ../server/nodejs
npm install

# Python（資料處理）
pip install pandas pyarrow
```

3. **轉換資料**
```bash
python scripts\convert_to_json.py
```

**日常開發**：

開啟兩個終端視窗：

```bash
# 終端 1: 啟動 Node.js 後端伺服器
cd server/nodejs
npm run dev
# 伺服器將在 http://localhost:5000 運行

# 終端 2: 啟動前端開發伺服器
cd frontend-app
npm run dev
# 前端將在 http://localhost:3000 運行
```

**生產模式**

```bash
# 建置前端
cd frontend-app
npm run build

# 建置並啟動後端（同時服務前端與API）
cd ../server/nodejs
npm run build
npm start
```

訪問: **http://localhost:5000**

### 替代方案：Python 後端

**使用 Python Parquet Server（推薦，節省空間）**：
```bash
cd server/python
python parquet_server.py --port 5000
```
- 無需預先轉換 JSON
- 即時從 Parquet 轉換
- 節省 80-90% 儲存空間

**使用 Python 靜態 Server**：
```bash
cd server/python
python static_server.py --port 5000
```
- 需要預先轉換 JSON（執行 `convert_to_json.py`）

---

## 📊 資料處理流程

### 1. 解碼（Quote → Parquet）⭐ 新版

將原始 Quote 檔案正確解碼成 Parquet 格式：

```bash
# 批次解碼所有日期
python scripts\batch_decode_quotes.py

# 或單日測試（2025-10-31）
python scripts\decode_quotes.py

# 驗證解碼結果
python scripts\verify_decode.py
```

功能：
- 讀取 `data/OTCQuote.*` 和 `data/TSEQuote.*`
- 正確解碼價格（除以 10000）
- 篩選漲停股票（當日 + 前一交易日）
- 輸出到 `data/decoded_quotes/{date}/{stock}.parquet`
- 支援多線程並行處理
- 自動跳過已處理檔案

### 2. 轉換（Parquet → JSON）可選

將 Parquet 轉換成靜態 JSON：

```bash
python scripts\convert_to_json.py
```

功能：
- 讀取 `data/decoded_quotes/` 下的 Parquet 檔案
- 計算所有指標（VWAP、內外盤、統計資料）
- 輸出到 `frontend/static/api/{date}/{stock}.json`
- 自動跳過已存在的檔案

**注意**：如果使用 `parquet_server.py`，可跳過此步驟（即時轉換）

---

## 🎯 使用說明

### 基本操作

1. **選擇日期** - 從下拉選單選擇交易日期
2. **選擇股票** - 選擇股票代碼
3. **查看資料** - 系統自動載入：
   - 價格走勢圖（含 VWAP）
   - 每分鐘累積成交量圖
   - 五檔報價表
   - 成交明細列表

### 時間軸控制

#### 播放控制
- **▶️ 播放/⏸ 暫停** - 開始或暫停時間軸回放
- **速度調整** - 支援 0.5x、1x、2x、4x 播放速度
- **時間軸滑桿** - 拖動跳轉到任意時間點

#### 圖表模式切換
- **Dynamic（動態）** - 只顯示當前時間之前的資料（預設）
- **Full（完整）** - 顯示完整09:00-13:30時間軸，已播放部分會標示

### 統一時間軸特性

系統採用**統一時間軸架構**，完整呈現市場變化：

- ✅ 五檔報價會在成交之間獨立更新
- ✅ 時間精確到毫秒（HH:MM:SS.mmm）
- ✅ 自動效能優化（超過50000個時間點啟用100ms過濾）
- ✅ 無動畫渲染，確保流暢播放

**範例**：
```
09:00:00.123 - 成交 A，五檔 A
09:00:01.456 - 五檔 B  ← 五檔獨立更新！
09:00:02.789 - 五檔 C  ← 五檔獨立更新！
09:00:03.012 - 成交 B，五檔 C
```

### 資料顯示

#### 五檔報價表
- **買盤（紅色）** - Bid 1~5，從上到下價格遞減
- **賣盤（綠色）** - Ask 1~5，從上到下價格遞增
- **視覺化長條** - 依成交量比例顯示
- **即時更新時間** - 顯示最新五檔的時間戳

#### 成交明細
- **時間** - 精確到毫秒
- **價格** - 成交價格（紅色=外盤，綠色=內盤）
- **單量** - 成交張數
- **內外盤** - 自動判斷（外盤/內盤/–）

---

## 🔧 開發指南

### 技術棧

#### 前端
- **React 18** - UI 框架
- **TypeScript 5** - 型別安全
- **Zustand** - 輕量狀態管理
- **Chart.js 4** - 圖表渲染
- **react-chartjs-2** - React Chart.js 整合
- **TailwindCSS 3** - 樣式框架
- **Vite** - 建置工具
- **Axios** - HTTP 客戶端

#### 後端
- **Node.js/TypeScript** - Express.js 高效能伺服器
- **Express.js 4** - Web 框架
- **Compression** - gzip 壓縮支援
- **CORS** - 跨域請求支援
- **Python 3.11+**（備用）- http.server 靜態檔案服務

#### 資料處理
- **Python** - Pandas, PyArrow
- **格式** - Parquet → JSON

#### 可選
- **Tauri 2.0** - 桌面應用打包

### 開發命令

```bash
# 前端開發
cd frontend-app
npm run dev          # 開發伺服器
npm run build        # 生產建置
npm run preview      # 預覽生產版本

# 後端開發
cd server/nodejs
npm run dev          # 開發伺服器（熱重載）
npm run build        # 編譯 TypeScript
npm start            # 啟動生產伺服器

# Tauri 桌面版（可選）
cd frontend-app
npm run tauri:dev    # 開發模式
npm run tauri:build  # 建置桌面應用
```

### API 端點

```
GET /api/dates
回應：["20251112", "20251111", ...]
```

```
GET /api/stocks/{date}
回應：["2330", "2317", ...]
```

```
GET /api/data/{date}/{stock_code}
回應：{
  chart: {...},          // 圖表資料（含 VWAP）
  depth: {...},          // 最新五檔
  depth_history: [...],  // 五檔歷史
  trades: [...],         // 成交明細（含內外盤）
  stats: {...},          // 統計資料
  stock_code: "2330",
  date: "20251112"
}
```

---

## 📝 維護與更新

### 新增資料

```bash
# 1. 放置新的 Quote 檔案到 data/ 目錄
# 2. 執行批次處理
cd scripts
python batch_process.py

# 3. 執行預處理
python preprocess.py

# 4. 重啟伺服器（如果正在運行）
```

### 清理快取

```bash
# 刪除 JSON 快取（會在下次預處理時重新產生）
rm -rf frontend/static/api/*
```

---

## 📤 GitHub 上傳指令

### 初次上傳

```bash
# 1. 初始化 Git（如果尚未初始化）
cd C:\Users\tacor\Documents\_01_github\_01_web
git init

# 2. 加入所有檔案（.gitignore 已排除大型資料檔案）
git add .

# 3. 建立第一個 commit
git commit -m "初始提交：台股即時報價回放系統

- React 18 + TypeScript 前端
- 統一時間軸架構
- 自動效能優化
- Chart.js 圖表視覺化
- Zustand 狀態管理"

# 4. 連接到 GitHub repository
git remote add origin https://github.com/your-username/stock-quote-playback.git

# 5. 推送到 GitHub
git push -u origin main
```

### 後續更新

```bash
# 1. 查看修改狀態
git status

# 2. 加入變更檔案
git add .

# 3. 提交變更
git commit -m "描述你的變更"

# 4. 推送到 GitHub
git push
```

### 注意事項

✅ `.gitignore` 已設定排除以下大型檔案：
- `data/` - 原始 Parquet 資料
- `frontend/static/api/` - JSON API 資料
- `*.parquet` - Parquet 檔案
- `node_modules/` - Node.js 依賴
- `dist/` `build/` - 建置輸出

⚠️ **這些資料不會上傳到 GitHub**，其他協作者需要自行處理資料或從其他來源獲取。

---

## 🐛 疑難排解

### 前端無法啟動

**問題**: `npm install` 失敗
**解決**: 確認 Node.js 版本 >= 18，刪除 `node_modules` 後重新安裝

**問題**: Port 3000 已被佔用
**解決**: Vite 會自動選擇其他 port（3001, 3002...），查看終端輸出的網址

### API 回傳 404

**問題**: 找不到資料
**解決**:
1. 確認後端伺服器已啟動在 `http://localhost:5000`
2. 執行 `scripts/preprocess.py` 產生 JSON 檔案
3. 檢查 `frontend/static/api/[日期]/` 目錄是否有 JSON 檔案

### 前端顯示空白或錯誤

**問題**: 統一時間軸建立失敗
**解決**:
1. 打開瀏覽器開發者工具（F12）查看 Console 錯誤
2. 確認 JSON 資料包含 `depth_history` 欄位
3. 檢查 `unifiedTimeline` 是否正確建立

**問題**: 圖表不顯示
**解決**:
1. 確認資料已載入（檢查 Network 標籤）
2. 檢查 Chart.js 依賴是否正確安裝
3. 查看 Console 是否有 JavaScript 錯誤

### 效能問題

**問題**: 播放時卡頓
**解決**:
1. 系統會自動啟用 100ms 過濾（超過 50000 個時間點）
2. 已停用 Chart.js 動畫
3. 如仍卡頓，可能是資料量過大，考慮增加過濾間隔

### Python 腳本錯誤

**問題**: 找不到資料目錄
**解決**: 確保從 `scripts/` 目錄執行腳本

**問題**: Parquet 讀取失敗
**解決**: 確認已安裝 `pandas` 和 `pyarrow`

---

## 📄 授權

本專案採用 MIT 授權。

---

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

---

## 📞 聯絡

如有問題或建議，請開 Issue 討論。

---

**享受極致效能的股票資料視覺化體驗！** 🚀
