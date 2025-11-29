# Scripts 資料處理腳本

這個資料夾包含所有資料處理和轉換的 Python 腳本。

## 📁 結構

```
scripts/
├── utils/                    # 共用工具模組 ⭐
│   ├── config.py            # 配置管理
│   ├── logger.py            # 日誌系統
│   ├── parser.py            # 資料解析函數
│   └── data_loader.py       # 資料載入函數
│
├── batch_decode.py          # 批次解碼 Quote 檔案 ⭐ 推薦
├── data_convert.py          # 轉換 Parquet → JSON ⭐ 推薦
└── query_stock.py           # 查詢單一股票資料 ⭐ 推薦
```

## 🚀 主要腳本說明

### 1. `batch_decode.py` - 批次解碼
將原始 OTC/TSEQuote 檔案解碼成 Parquet 格式。

```bash
python scripts/batch_decode.py
```

功能：
- 讀取 `data/OTCQuote.*` 和 `data/TSEQuote.*`
- 正確解碼價格（除以 10000）
- 篩選漲停股票
- 輸出到 `data/decoded_quotes/{date}/{stock}.parquet`
- 支援多線程並行處理

### 2. `data_convert.py` - 資料轉換
將 Parquet 轉換成靜態 JSON API 檔案。

```bash
python scripts/data_convert.py
```

功能：
- 讀取 `data/decoded_quotes/` 下的 Parquet 檔案
- 計算所有指標（VWAP、內外盤、統計資料）
- 輸出到 `frontend/static/api/{date}/{stock}.json`

### 3. `query_stock.py` - 查詢股票
查詢單一股票的資料。

```bash
python scripts/query_stock.py 2330 20251112
```

## 📦 共用工具模組 (utils/)

所有腳本共用的核心功能，避免程式碼重複：

- **config.py** - 集中管理所有路徑和配置參數
- **logger.py** - 統一的日誌輸出系統
- **parser.py** - Trade/Depth 資料解析函數
- **data_loader.py** - 漲停清單載入和股票篩選

## 🔧 使用流程

```bash
# 1. 解碼原始檔案
python scripts/batch_decode.py

# 2. 轉換成 JSON（可選，如使用 parquet_server.py 可跳過）
python scripts/data_convert.py

# 3. 查詢特定股票
python scripts/query_stock.py 2330 20251112
```

## 💡 進階提示

- **自動跳過已處理檔案**：所有腳本都會自動跳過已存在的輸出檔案
- **多線程處理**：batch_decode.py 預設使用 4 個 worker
- **日誌輸出**：所有操作都有詳細的日誌記錄

## 📋 依賴套件

```bash
pip install pandas pyarrow
```
