# 使用指南

## 快速開始

### 方案 A：使用預先轉換的 JSON（推薦新手）

這是最簡單的方式，適合第一次使用。

**步驟 1：轉換資料**
```bash
cd C:\Users\User\Documents\_web\_01_web
python scripts/convert_to_json.py
```

**步驟 2：啟動 Server**
```bash
cd server\python
python static_server.py --port 5000
```

**步驟 3：開啟瀏覽器**
```
http://localhost:5000
```

### 方案 B：使用 Parquet 即時轉換（推薦進階）

節省空間，無需預先轉換。

**步驟 1：啟動 Parquet Server**
```bash
cd C:\Users\User\Documents\_web\_01_web\server\python
python parquet_server.py --port 5000
```

**步驟 2：開啟瀏覽器**
```
http://localhost:5000
```

## 完整工作流程

### 1. 解碼 Quote 資料

**單日測試**（測試 2025-10-31）：
```bash
cd C:\Users\User\Documents\_web\_01_web
python scripts/decode_quotes.py
```

**批次處理**（處理所有日期）：
```bash
cd C:\Users\User\Documents\_web\_01_web
python scripts/batch_decode_quotes.py
```

**驗證結果**：
```bash
python scripts/verify_decode.py
```

**輸出位置**：
```
data/decoded_quotes/
├── 20251031/
│   ├── 1503.parquet
│   ├── 1514.parquet
│   └── ...
├── 20251103/
└── ...
```

### 2. 轉換為 JSON（可選）

如果使用方案 A，需要執行此步驟：

```bash
python scripts/convert_to_json.py
```

**輸出位置**：
```
frontend/static/api/
├── 20251031/
│   ├── 1503.json
│   ├── 1514.json
│   └── ...
├── 20251103/
└── ...
```

### 3. 啟動 Server

**選項 1：靜態 Server（需要預先轉換）**
```bash
cd server\python
python static_server.py --port 5000
```

**選項 2：Parquet Server（即時轉換）**
```bash
cd server\python
python parquet_server.py --port 5000
```

**選項 3：Node.js Server（需要預先轉換）**
```bash
cd server\nodejs
npm install
npm run build
npm start
```

### 4. 開發前端（可選）

如果需要修改前端：

```bash
cd frontend-app
npm install
npm run dev
```

開發 server 會自動啟動在 `http://localhost:5173`

## API 使用

所有 server 都提供相同的 RESTful API：

### 取得所有日期
```http
GET /api/dates
```

**回應範例**：
```json
[
  "20251031",
  "20251103",
  "20251104"
]
```

### 取得指定日期的股票清單
```http
GET /api/stocks/{date}
```

**範例**：
```http
GET /api/stocks/20251031
```

**回應範例**：
```json
[
  "1503",
  "1514",
  "1519",
  "2368",
  "3105"
]
```

### 取得股票資料
```http
GET /api/data/{date}/{stock}
```

**範例**：
```http
GET /api/data/20251031/3105
```

**回應範例**：
```json
{
  "chart": {
    "timestamps": ["2025-10-31 08:41:29.033157", ...],
    "prices": [95.0, 95.0, ...],
    "volumes": [558, 558, ...],
    "total_volumes": [558, 1116, ...],
    "vwap": [95.0, 95.0, ...]
  },
  "depth": {
    "bids": [
      {"price": 107.5, "volume": 51},
      {"price": 107.0, "volume": 4}
    ],
    "asks": [
      {"price": 108.0, "volume": 35},
      {"price": 108.5, "volume": 20}
    ],
    "timestamp": "2025-10-31 13:30:00.000000"
  },
  "depth_history": [...],
  "trades": [...],
  "stats": {
    "current_price": 107.5,
    "open_price": 95.0,
    "high_price": 107.5,
    "low_price": 88.1,
    "avg_price": 107.08,
    "total_volume": 24500,
    "trade_count": 3730,
    "change": 12.5,
    "change_pct": 13.16
  },
  "stock_code": "3105",
  "date": "20251031"
}
```

## 前端功能

開啟 `http://localhost:5000` 後，您可以：

1. **選擇日期**：從下拉選單選擇要查看的日期
2. **選擇股票**：從股票清單選擇要查看的股票代碼
3. **查看圖表**：
   - 價格走勢圖
   - 成交量圖
   - VWAP 線
4. **查看五檔**：即時買賣盤五檔報價
5. **查看成交明細**：所有成交記錄，包含內外盤判斷
6. **時間軸控制**：可以回放交易過程

## 常見問題

### Q: 找不到 pandas 模組

**A:** 安裝 pandas：
```bash
pip install pandas pyarrow
```

### Q: 轉換很慢

**A:** 這是正常的。對於大量資料，建議：
1. 使用方案 B（Parquet Server），無需預先轉換
2. 或者讓轉換程式在背景執行，只需轉換一次

### Q: Server 無法啟動

**A:** 檢查：
1. Port 5000 是否被佔用
2. Python 版本（需要 3.8+）
3. 是否安裝了所有依賴

### Q: 前端顯示錯誤

**A:** 檢查：
1. Server 是否正常運行
2. 瀏覽器 Console 是否有錯誤訊息
3. API 端點是否正確回應

### Q: 資料不完整

**A:** 重新解碼：
```bash
python scripts/batch_decode_quotes.py
```

### Q: 如何更新資料

**A:**
1. 將新的 Quote 檔案放到 `data/` 目錄
2. 執行解碼程式：`python scripts/batch_decode_quotes.py`
3. 如果使用方案 A，重新轉換：`python scripts/convert_to_json.py`
4. 如果使用方案 B，server 會自動讀取新資料

## 檔案結構

```
C:\Users\User\Documents\_web\_01_web\
├── data/
│   ├── decoded_quotes/           # Parquet 解碼資料（新）
│   │   ├── 20251031/
│   │   │   ├── 1503.parquet
│   │   │   └── ...
│   │   └── ...
│   ├── processed_data/           # 舊資料（可刪除）
│   ├── OTCQuote.20251031         # 原始 Quote 檔案
│   ├── TSEQuote.20251031
│   └── lup_ma20_filtered.parquet # 漲停股票清單
│
├── frontend/
│   ├── static/
│   │   └── api/                  # JSON 資料（方案 A）
│   │       ├── 20251031/
│   │       └── ...
│   └── index.html
│
├── frontend-app/                 # React 前端應用
│   ├── src/
│   └── dist/                     # 打包後的檔案
│
├── server/
│   ├── python/
│   │   ├── static_server.py      # 靜態 JSON Server
│   │   └── parquet_server.py     # Parquet Server（推薦）
│   └── nodejs/
│       └── src/
│           ├── server.ts         # Node.js JSON Server
│           └── parquet-server.ts # Node.js Parquet Server
│
└── scripts/
    ├── decode_quotes.py          # 單日解碼
    ├── batch_decode_quotes.py    # 批次解碼
    ├── convert_to_json.py        # Parquet 轉 JSON
    └── verify_decode.py          # 驗證資料
```

## 效能建議

### 開發環境
- 使用 **Parquet Server**（方案 B）
- 節省轉換時間和儲存空間
- 資料更新立即生效

### 生產環境
- 使用 **預先轉換 + 靜態 Server**（方案 A）
- 最快的回應速度
- 可以使用 CDN 加速

### 儲存空間
- Parquet: ~5-10 MB / 21支股票
- JSON: ~50-100 MB / 21支股票
- **建議**：保留 Parquet，JSON 可選

## 下一步

1. 查看 `DECODE_SUMMARY.md` 了解解碼程式的詳細資訊
2. 查看 `ARCHITECTURE_UPDATE.md` 了解架構變更
3. 查看 `scripts/README_DECODE.md` 了解解碼規格

## 聯絡與支援

如有問題，請查看：
- `DECODE_SUMMARY.md` - 任務完成總結
- `ARCHITECTURE_UPDATE.md` - 架構更新說明
- `scripts/README_DECODE.md` - 解碼程式說明

---

**更新日期**：2025-11-20
**版本**：2.0
