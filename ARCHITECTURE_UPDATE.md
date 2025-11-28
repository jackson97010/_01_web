# 架構更新說明

## 概述

已將整個系統更新為使用新的解碼資料架構，從原本的 `frontend/static/api` JSON 檔案改為直接使用 `data/decoded_quotes` 中的 Parquet 檔案。

## 資料流程

### 舊架構
```
OTC/TSEQuote.YYYYMMDD (原始檔案)
  ↓ (舊的 batch_process.py)
data/processed_data/{date}/{stock}.parquet
  ↓ (需要額外轉換)
frontend/static/api/{date}/{stock}.json
  ↓ (靜態提供)
Server → Frontend
```

### 新架構（推薦）
```
OTC/TSEQuote.YYYYMMDD (原始檔案)
  ↓ (新的 decode_quotes.py / batch_decode_quotes.py)
data/decoded_quotes/{date}/{stock}.parquet
  ↓ (即時轉換或預先轉換)
Server → Frontend
```

## 新增的程式

### 1. 解碼程式（已完成）

#### `scripts/decode_quotes.py`
- 單日測試程式
- 測試 OTC/TSE Quote 檔案解碼
- 輸出到 `data/decoded_quotes/`

#### `scripts/batch_decode_quotes.py`
- 批次處理所有日期
- 支援多線程（4線程）
- 自動跳過已處理的檔案

#### `scripts/verify_decode.py`
- 驗證解碼結果
- 檢查資料完整性

### 2. 資料轉換程式

#### `scripts/convert_to_json.py`
- 將 Parquet 檔案預先轉換為 JSON
- 輸出到 `frontend/static/api/`
- 適合靜態部署（不需要在 runtime 轉換）

**使用時機**：
- 靜態網站部署
- 希望最快的回應速度
- 不在意儲存空間

**執行方式**：
```bash
python scripts/convert_to_json.py
```

### 3. Server 程式

#### `server/python/parquet_server.py` ⭐ 推薦
- 直接讀取 Parquet 檔案
- 即時轉換為 JSON 格式
- 節省儲存空間
- 無需預先轉換

**優點**：
- 節省磁碟空間（Parquet 比 JSON 小很多）
- 資料更新後立即生效
- 不需要額外的轉換步驟

**啟動方式**：
```bash
cd server/python
python parquet_server.py --port 5000
```

#### `server/python/static_server.py`
- 原有的靜態檔案伺服器
- 提供預先轉換的 JSON 檔案
- 適合已經轉換好的情境

**啟動方式**：
```bash
cd server/python
python static_server.py --port 5000
```

#### `server/nodejs/src/parquet-server.ts`
- Node.js 版本的 Parquet 伺服器
- 即時轉換 Parquet 為 JSON
- 需要安裝 `parquet-wasm` 套件

**安裝依賴**：
```bash
cd server/nodejs
npm install parquet-wasm
```

**啟動方式**：
```bash
cd server/nodejs
npm run build
npm start
```

#### `server/nodejs/src/server.ts`
- 原有的 Node.js 伺服器
- 提供預先轉換的 JSON 檔案

## 使用建議

### 方案 A：即時轉換（推薦）⭐

**適合**：
- 開發環境
- 資料經常更新
- 儲存空間有限

**步驟**：
1. 執行解碼程式：
   ```bash
   python scripts/batch_decode_quotes.py
   ```

2. 啟動 Parquet Server：
   ```bash
   cd server/python
   python parquet_server.py --port 5000
   ```

3. 訪問前端：
   ```
   http://localhost:5000
   ```

**優點**：
- ✅ 節省空間（只需要 Parquet 檔案）
- ✅ 資料更新立即生效
- ✅ 無需額外轉換步驟

**缺點**：
- ⚠️ 首次載入略慢（需要即時轉換）
- ⚠️ Server 需要安裝 pandas

### 方案 B：預先轉換

**適合**：
- 生產環境
- 靜態網站部署
- 追求最快回應速度

**步驟**：
1. 執行解碼程式：
   ```bash
   python scripts/batch_decode_quotes.py
   ```

2. 轉換為 JSON：
   ```bash
   python scripts/convert_to_json.py
   ```

3. 啟動靜態 Server：
   ```bash
   cd server/python
   python static_server.py --port 5000
   ```

**優點**：
- ✅ 最快的回應速度
- ✅ Server 不需要 pandas
- ✅ 可以部署到任何靜態主機

**缺點**：
- ⚠️ 需要雙倍儲存空間（Parquet + JSON）
- ⚠️ 資料更新需要重新轉換

## 資料格式對比

### Parquet 格式（解碼後）

**位置**：`data/decoded_quotes/{date}/{stock}.parquet`

**欄位**：
```
Trade 記錄：
- Type: 'Trade'
- StockCode: 股票代碼
- Datetime: 完整時間
- Timestamp: 原始時間戳
- Flag: 試撮旗標
- Price: 成交價
- Volume: 成交量
- TotalVolume: 總成交量

Depth 記錄：
- Type: 'Depth'
- StockCode: 股票代碼
- Datetime: 完整時間
- Timestamp: 原始時間戳
- BidCount, AskCount: 買賣盤檔數
- Bid1_Price ~ Bid5_Price: 買盤價格
- Bid1_Volume ~ Bid5_Volume: 買盤數量
- Ask1_Price ~ Ask5_Price: 賣盤價格
- Ask1_Volume ~ Ask5_Volume: 賣盤數量
```

### JSON 格式（前端格式）

**位置**：`frontend/static/api/{date}/{stock}.json`

**結構**：
```json
{
  "chart": {
    "timestamps": [],
    "prices": [],
    "volumes": [],
    "total_volumes": [],
    "vwap": []
  },
  "depth": {
    "bids": [],
    "asks": [],
    "timestamp": ""
  },
  "depth_history": [],
  "trades": [],
  "stats": {},
  "stock_code": "",
  "date": ""
}
```

## API 端點

所有 server 都提供相同的 API：

```
GET /api/dates
回應: ["20251031", "20251103", ...]

GET /api/stocks/{date}
回應: ["1503", "1514", "1519", ...]

GET /api/data/{date}/{stock}
回應: { chart, depth, trades, stats, ... }
```

## 前端無需修改

前端 (`frontend-app`) 無需任何修改！

- API 端點保持不變
- 回應格式保持不變
- 只需要選擇使用哪個 server

## 儲存空間對比

以 2025-10-31 的資料為例（21支股票）：

```
Parquet 檔案：約 5-10 MB
JSON 檔案：約 50-100 MB

節省空間：80-90%
```

## 效能對比

### 靜態 JSON Server
- 回應時間：~10ms
- 記憶體使用：低
- CPU 使用：幾乎為 0

### Parquet Server（即時轉換）
- 回應時間：~50-100ms（首次）
- 回應時間：~10ms（有快取）
- 記憶體使用：中等
- CPU 使用：中等

## 遷移步驟

### 從舊架構遷移到新架構

1. **備份現有資料**：
   ```bash
   cp -r data/processed_data data/processed_data.backup
   cp -r frontend/static/api frontend/static/api.backup
   ```

2. **執行新的解碼程式**：
   ```bash
   python scripts/batch_decode_quotes.py
   ```

3. **選擇部署方式**：

   **方式 A（即時轉換）**：
   ```bash
   cd server/python
   python parquet_server.py --port 5000
   ```

   **方式 B（預先轉換）**：
   ```bash
   python scripts/convert_to_json.py
   cd server/python
   python static_server.py --port 5000
   ```

4. **測試**：
   - 訪問 http://localhost:5000
   - 檢查各個日期和股票的資料
   - 確認圖表、五檔、成交明細都正常顯示

5. **清理舊資料**（可選）：
   ```bash
   rm -rf data/processed_data.backup
   # 如果使用方案 A，可以刪除 JSON 檔案
   rm -rf frontend/static/api
   ```

## 故障排除

### 問題：找不到 parquet 檔案

**檢查**：
```bash
ls data/decoded_quotes/20251031/
```

**解決**：執行解碼程式
```bash
python scripts/batch_decode_quotes.py
```

### 問題：Server 回應 500 錯誤

**檢查**：Server 日誌中的錯誤訊息

**可能原因**：
1. Parquet 檔案損壞
2. 缺少 pandas 套件
3. 檔案權限問題

**解決**：
```bash
# 重新安裝 pandas
pip install pandas pyarrow

# 重新解碼
python scripts/batch_decode_quotes.py
```

### 問題：轉換速度太慢

**解決**：
1. 使用預先轉換方案（方案 B）
2. 增加 Python 的記憶體限制
3. 只轉換需要的日期

## 總結

✅ 新架構優點：
- 解碼邏輯更清晰、正確
- 節省儲存空間（使用 Parquet）
- 彈性更高（可選即時轉換或預先轉換）
- 更容易維護和擴展

✅ 推薦配置：
- 開發環境：方案 A（Parquet Server）
- 生產環境：方案 B（預先轉換 + 靜態 Server）

---

**更新日期**：2025-11-20
**版本**：2.0
