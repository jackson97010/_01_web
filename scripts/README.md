# Scripts - 資料處理工具

台股即時報價回放系統的資料處理工具集。

## 📁 目錄結構

```
scripts/
├── utils/              # 共用工具模組
│   ├── config.py      # 配置管理
│   ├── logger.py      # 日誌系統
│   ├── parser.py      # Quote 資料解析
│   └── data_loader.py # 資料載入
│
├── decode.py          # Quote 檔案批次解碼
├── convert.py         # Parquet → JSON 轉換
└── query.py           # 單一股票查詢
```

## 🚀 主要工具

### 1. `decode.py` - Quote 檔案解碼

將原始 OTC/TSE Quote 檔案解碼成 Parquet 格式。

```bash
python scripts/decode.py
```

**功能：**
- 讀取 `data/OTCQuote.*` 和 `data/TSEQuote.*`
- 正確解碼價格（除以 10000）
- 篩選漲停股票（從 `lup_ma20_filtered.parquet`）
- 輸出到 `data/decoded_quotes/{date}/{stock}.parquet`
- 支援多線程並行處理（預設 4 線程）

**性能優化：**
- 使用大 buffer (1MB) 提升 I/O 效能
- 快速字符串過濾減少解析次數
- Snappy 壓縮提升讀寫速度

### 2. `convert.py` - 資料轉換

將 Parquet 轉換成靜態 JSON API 檔案。

```bash
python scripts/convert.py
```

**功能：**
- 讀取 `data/decoded_quotes/` 下的 Parquet 檔案
- 計算所有指標（VWAP、內外盤、統計資料）
- 輸出到 `frontend/static/api/{date}/{stock}.json`
- 支援多進程並行處理

**資料格式：**
```json
{
  "chart": {
    "timestamps": [...],
    "prices": [...],
    "volumes": [...],
    "total_volumes": [...],
    "vwap": [...]
  },
  "depth": {
    "bids": [{"price": 100.5, "volume": 100}, ...],
    "asks": [{"price": 101.0, "volume": 50}, ...],
    "timestamp": "2025-11-12 09:00:00"
  },
  "depth_history": [...],
  "trades": [...],
  "stats": {
    "current_price": 100.5,
    "open_price": 100.0,
    "high_price": 101.0,
    "low_price": 99.5,
    "avg_price": 100.25,
    "total_volume": 10000,
    "trade_count": 500,
    "change": 0.5,
    "change_pct": 0.5
  }
}
```

### 3. `query.py` - 單一股票查詢

從原始 Quote 檔案快速查詢單一股票資料。

```bash
# 顯示到控制台
python scripts/query.py 20251112 TSE 2330 --output console

# 儲存為 Parquet
python scripts/query.py 20251112 OTC 8042 --output parquet

# 儲存為 JSON
python scripts/query.py 20251112 TSE 2330 --output json
```

**參數：**
- `date`: 日期 (YYYYMMDD)
- `market`: 市場別 (OTC/TSE)
- `stock_code`: 股票代號
- `--output`: 輸出格式 (console/parquet/json)

## 📦 Utils 工具模組

### config.py - 配置管理
集中管理所有路徑和配置參數：
- 專案目錄路徑
- 資料檔案路徑
- 處理參數（線程數、價格除數等）

### logger.py - 日誌系統
統一的日誌輸出系統，支援：
- 彩色輸出
- 時間戳記
- 多級別日誌（INFO/WARNING/ERROR）

### parser.py - 資料解析
Quote 資料解析函數：
- `parse_trade_line()` - 解析成交資料
- `parse_depth_line()` - 解析五檔資料
- `parse_timestamp()` - 解析時間戳

### data_loader.py - 資料載入
資料載入和篩選：
- `load_limit_up_list()` - 載入漲停清單
- `get_target_stocks()` - 取得目標股票
- `read_quote_file()` - 讀取並解析 Quote 檔案

## 🔧 使用流程

```bash
# 1. 解碼原始檔案
python scripts/decode.py

# 2. 轉換成 JSON（如使用 Parquet Server 可跳過）
python scripts/convert.py

# 3. 查詢特定股票（可選）
python scripts/query.py 20251112 TSE 2330 --output console
```

## 📊 Quote 資料格式說明

### Trade 格式
```
Trade,股票代碼,成交時間,試撮旗標,成交價,成交單量,成交總量[,序號]
```
- **試撮旗標**: 0=一般揭示, 1=試算揭示
- **成交價**: 4位小數，需除以 10000
- **範例**: `Trade,2355,131219825776,0,333500,1,1530` → 成交價 33.35

### Depth 格式
```
Depth,股票代碼,報價時間,BID:檔數,買盤...,ASK:檔數,賣盤...[,序號]
```
- **檔位格式**: 價格*數量
- **價格**: 4位小數，需除以 10000
- **範例**: `BID:5,333000*27,332500*5,...,ASK:5,333500*17,334000*5,...`

### 時間戳格式
- **格式**: HHMMSSffffff (12位)
- **範例**: 131219825776 → 13:12:19.825776

## 💡 進階功能

### 自動跳過已處理檔案
所有工具都會檢查輸出檔案，自動跳過已處理的檔案。

### 多線程/多進程處理
- `decode.py`: 預設使用 4 個線程
- `convert.py`: 預設使用 4 個進程
- 可在 `utils/config.py` 調整 `DEFAULT_MAX_WORKERS`

### 日誌輸出
所有操作都有詳細的日誌記錄，包括：
- 處理進度
- 成功/跳過/錯誤數量
- 處理時間統計

## 📋 依賴套件

```bash
pip install pandas pyarrow
```

## 🎯 效能優化重點

1. **I/O 優化**
   - 使用大 buffer (1MB) 讀取檔案
   - Snappy 壓縮提升讀寫速度

2. **資料處理優化**
   - 快速字符串過濾
   - 向量化計算（VWAP、累計成交量）
   - 減少重複計算

3. **並行處理**
   - 多線程處理日期
   - 多進程處理檔案轉換

4. **記憶體優化**
   - 使用 inplace 操作
   - 及時釋放大型物件

## 📝 注意事項

1. **漲停清單檔案**：必須存在 `data/lup_ma20_filtered.parquet`
2. **原始資料檔案**：格式為 `OTCQuote.YYYYMMDD` 和 `TSEQuote.YYYYMMDD`
3. **日期邏輯**：解析日期 D 時，會包含 D 和 D-1 交易日的漲停股票
4. **假日處理**：自動向前搜尋最多 7 天找到前一交易日

## 🔍 故障排除

### 找不到漲停清單檔案
```
錯誤: 找不到漲停清單 data/lup_ma20_filtered.parquet
```
**解決**：確保漲停清單檔案存在於正確位置。

### 找不到 Quote 檔案
```
未找到 OTCQuote.20251112
```
**解決**：確認 `data/` 目錄下有對應日期的 Quote 檔案。

### 記憶體不足
**解決**：調整 `utils/config.py` 中的 `DEFAULT_MAX_WORKERS` 減少並行數量。

---

**版本**: 2.0
**最後更新**: 2025-11-30
