# OTC/TSE Quote 資料處理與視覺化專案

## 專案目標

建立一個自動化系統來處理台灣證券交易所（TSE）和櫃買中心（OTC）的 tick 資料，並提供網頁視覺化介面。

## 需求說明

### 1. 批次資料處理
- **輸入檔案**：
  - `OTCQuote.YYYYMMDD` - 櫃買中心逐筆資料
  - `TSEQuote.YYYYMMDD` - 證交所逐筆資料
  - `lup_ma20_filtered.parquet` - 漲停股票清單（包含 date, stock_id, close_price, limit_up_price）

- **處理邏輯**：
  - 自動掃描目錄中所有 Quote 檔案
  - 對每個日期的檔案，只保存以下股票的 tick 資料：
    - 當日漲停的股票
    - 前一日漲停的股票
  - 其他股票資料不保存（節省儲存空間）

- **輸出格式**：
  - 按日期建立目錄：`YYYYMMDD/`
  - 每支股票儲存為：`YYYYMMDD/{stock_code}.parquet`
  - 包含 Trade（成交）和 Depth（五檔）資料

### 2. 資料格式

**Trade 資料**（成交明細）：
```
Trade,股票代碼,時間戳,Flag,價格,數量,總量
```

**Depth 資料**（五檔報價）：
```
Depth,股票代碼,時間戳,BID:count,買1價格*數量,...買5,ASK:count,賣1價格*數量,...賣5
```

**處理後的欄位**：
- Trade: Type, StockCode, Timestamp, Datetime, Flag, Price, Volume, TotalVolume
- Depth: Type, StockCode, Timestamp, Datetime, BidCount, Bid1_Price, Bid1_Volume, ..., Bid5_Volume, AskCount, Ask1_Price, Ask1_Volume, ..., Ask5_Volume

### 3. 網頁視覺化介面

參考 sample.png 的樣式，建立即時資料瀏覽器：

**功能模組**：
1. **走勢圖**（左側主圖）
   - 分時價格線圖（黃色/綠色線）
   - 成交量柱狀圖（底部紫色/綠色柱）
   - 時間軸顯示

2. **五檔報價**（右上角）
   - 買進五檔（粉紅色背景）
   - 賣出五檔（黑色背景）
   - 顯示價格和數量
   - 內外盤佔比視覺化

3. **成交明細**（右下角）
   - 時間、買進/賣出、成交價、單量、總量
   - 即時更新顯示

4. **股票資訊**（頂部）
   - 股票代碼、名稱
   - 現價、漲跌、漲跌幅
   - 最高、最低、開盤、成交值等資訊

**技術棧**：
- Backend: Python Flask
- Frontend: HTML + JavaScript + Chart.js/ECharts
- Data: 讀取 parquet 檔案

### 4. 執行環境

- Conda 環境：`my_project`
- 啟動命令：`conda activate my_project`

## 實作計畫

### 檔案結構
```
.
├── batch_process.py          # 批次處理腳本
├── web_viewer.py             # 網頁伺服器
├── templates/
│   └── viewer.html           # 網頁模板
├── static/
│   ├── css/
│   │   └── style.css        # 樣式表
│   └── js/
│       └── chart.js         # 圖表邏輯
├── requirements.txt          # Python 套件依賴
├── run_batch.bat            # Windows 批次處理執行腳本
└── run_viewer.bat           # Windows 網頁伺服器執行腳本
```

### 工作步驟

1. **建立批次處理腳本** (`batch_process.py`)
   - 讀取漲停清單
   - 掃描 Quote 檔案
   - 過濾並解析資料
   - 儲存為 parquet

2. **建立網頁視覺化** (`web_viewer.py` + templates)
   - Flask API 端點
   - 前端圖表顯示
   - 資料載入與更新

3. **建立執行腳本**
   - Conda 環境啟動
   - 批次處理執行
   - 網頁伺服器啟動

4. **測試與優化**
   - 測試資料處理流程
   - 測試網頁顯示效果
   - 效能優化

## 預期成果

1. 自動化處理所有日期的 Quote 檔案，只保存漲停相關股票
2. 大幅減少儲存空間（只保存必要資料）
3. 提供美觀的網頁介面瀏覽 tick 資料
4. 支援選擇日期和股票查看詳細資訊

## 開始執行

確認需求無誤後，開始實作各個模組。
