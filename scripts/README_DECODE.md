# OTC/TSE Quote 資料解碼程式說明

## 概述

本專案提供了正確的 OTC/TSE Quote 資料解碼程式，根據官方文件規格實現：

```
OTC/TSEQuote.{Y-M-D} 資料內部細節

1. 成交格式 (Trade):
   Trade,股票代碼,成交時間,試撮旗標,成交價,成交單量,成交總量[,序號]
   - 試撮旗標: 0=一般揭示, 1=試算揭示
   - 成交價: 4位小數，需除以 10000
   - 例如: 333500 -> 33.35

2. 五檔格式 (Depth):
   Depth,股票代碼,報價時間,BID:委買檔數,買盤檔位...,ASK:委賣檔數,賣盤檔位...[,序號]
   - 檔位格式: 價格*數量
   - 價格: 4位小數，需除以 10000
```

## 程式檔案

### 1. `decode_quotes.py` - 單日測試程式

用於測試單個日期的解碼功能。

**功能**:
- 解析指定日期（預設 2025-10-31）的 OTC 和 TSE Quote 資料
- 只解析 lup_ma20_filtered.parquet 中當日和前一交易日的漲停股票
- 輸出到 `data/decoded_quotes/{日期}/` 目錄

**使用方法**:
```bash
python scripts/decode_quotes.py
```

**輸出範例**:
```
data/decoded_quotes/20251031/
├── 1503.parquet
├── 1514.parquet
├── 3105.parquet
└── ...
```

### 2. `batch_decode_quotes.py` - 批次處理程式

用於批次處理所有日期的 Quote 檔案。

**功能**:
- 自動掃描 `data/` 目錄下所有 OTCQuote.* 和 TSEQuote.* 檔案
- 從 lup_ma20_filtered.parquet 讀取漲停股票清單
- 對每個日期，解析當日和前一交易日漲停股票的資料
- 支援多線程並行處理（預設最多 4 個線程）
- 自動跳過已處理的檔案

**使用方法**:
```bash
python scripts/batch_decode_quotes.py
```

**輸出結構**:
```
data/decoded_quotes/
├── 20251031/
│   ├── 1503.parquet
│   ├── 1514.parquet
│   └── ...
├── 20251103/
│   └── ...
└── ...
```

## 解碼規則

### Trade 資料欄位

| 欄位 | 說明 | 資料型別 |
|------|------|---------|
| Type | 資料類型（Trade） | string |
| StockCode | 股票代碼 | string |
| Datetime | 日期時間 | datetime64 |
| Timestamp | 時間戳（原始） | int64 |
| Flag | 試撮旗標（0/1） | int |
| Price | 成交價（已除以10000） | float |
| Volume | 成交單量 | int |
| TotalVolume | 成交總量 | int |

### Depth 資料欄位

| 欄位 | 說明 | 資料型別 |
|------|------|---------|
| Type | 資料類型（Depth） | string |
| StockCode | 股票代碼 | string |
| Datetime | 日期時間 | datetime64 |
| Timestamp | 時間戳（原始） | int64 |
| BidCount | 買盤檔數 | int |
| AskCount | 賣盤檔數 | int |
| Bid1_Price ~ Bid5_Price | 買盤1-5檔價格 | float |
| Bid1_Volume ~ Bid5_Volume | 買盤1-5檔數量 | int |
| Ask1_Price ~ Ask5_Price | 賣盤1-5檔價格 | float |
| Ask1_Volume ~ Ask5_Volume | 賣盤1-5檔數量 | int |

## 關鍵修正點

### 1. 價格轉換
- ✅ **正確**: 所有價格都除以 10000（4位小數）
  - Trade 的成交價
  - Depth 的買賣盤檔位價格

### 2. 時間戳解析
- ✅ **正確**: 時間戳為 HHMMSSffffff 格式（12位）
  - 補0到12位
  - 格式: `YYYYMMDD` + `HHMMSSffffff`

### 3. Depth 資料解析
- ✅ **正確**: 正確處理可能存在的序號欄位
  - 如果最後一個欄位不包含 `*`，則視為序號
  - 買盤檔位：BID 之後到 ASK 之前
  - 賣盤檔位：ASK 之後到序號之前（或結尾）

## 測試驗證

已使用 OTCQuote.20251031 和 TSEQuote.20251031 進行測試驗證：

```python
# 測試結果
股票 3105 (2025-10-31):
- 總記錄: 17,606 筆（3,730 Trade + 13,876 Depth）
- Trade 價格範圍: 88.1 ~ 107.5
- 時間範圍: 08:41:29 ~ 13:30:00
- 資料完整性: ✅ 正確

範例 Trade 記錄:
- 時間: 08:41:29.033157
- 試撮旗標: 1 (試算揭示)
- 成交價: 95.0
- 成交量: 558

範例 Depth 記錄:
- 時間: 08:41:29.033157
- 買1: 95.0 * 51
- 買2: 94.9 * 4
- 賣1: 96.0 * 35
```

## 與舊程式的比較

### batch_process.py (舊版)
- ✅ 價格轉換正確（除以 10000）
- ✅ 時間戳解析正確
- ✅ Depth 格式解析正確
- ⚠️ 程式碼較複雜，可讀性較低
- ⚠️ 輸出目錄為 `data/processed_data/`

### decode_quotes_correct.py (新版 - 2025-11-28 更新)
- ✅ 所有解碼邏輯與舊版一致（解碼方式正確）
- ✅ 程式碼更清晰、可讀性更高
- ✅ 更詳細的註解說明
- ✅ 更好的錯誤處理
- ✅ 輸出目錄為 `data/decoded_quotes/`
- ✅ 完整的測試驗證（test_decode_both.py）
- ✅ 支援同時處理 OTC 和 TSE 檔案

## 最新測試結果 (2025-11-28)

已使用 OTCQuote.20251031 和 TSEQuote.20251031 進行完整測試：

```
測試日期: 2025-10-31
需要處理的股票數: 21 支
- 前一交易日 (2025-10-30): 10 支
- 當日 (2025-10-31): 11 支

處理結果:
✅ 所有 21 支股票都已成功處理
✅ OTC 檔案處理: 8 支股票
✅ TSE 檔案處理: 13 支股票

範例驗證:
- 1503 (台塑): 42,079 筆記錄, 價格範圍 180.00 ~ 199.50
- 1514: 28,095 筆記錄, 價格範圍 100.50 ~ 110.50
- 1519: 22,677 筆記錄, 價格範圍 651.00 ~ 715.00
- 3105: 17,606 筆記錄, 價格範圍 88.10 ~ 107.50
```

## 使用新程式

### 批次處理所有檔案
```bash
python scripts/decode_quotes_correct.py
```

### 測試單個日期
```bash
python scripts/test_decode_both.py
```

## 注意事項

1. **股票清單來源**:
   - 需要 `data/lup_ma20_filtered.parquet` 檔案
   - 包含漲停股票的日期和代碼

2. **資料檔案**:
   - OTCQuote.{YYYYMMDD}: 櫃買市場
   - TSEQuote.{YYYYMMDD}: 上市市場

3. **日期邏輯**:
   - 對於日期 D，會解析 D 和 D-1 交易日的漲停股票
   - 自動處理週末和假日（向前找最多7天）

4. **檔案格式**:
   - 輸出為 Parquet 格式
   - 每支股票一個檔案
   - 資料按時間排序

## 效能

- 單個日期處理時間: 約 5-10 秒
- 批次處理支援多線程（預設 4 線程）
- 自動跳過已處理的檔案

## 授權

© 2025 量化交易系統
