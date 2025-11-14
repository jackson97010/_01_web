# OTC/TSE Quote 資料處理與視覺化系統

完整的台股逐筆資料處理與網頁視覺化系統。

## 功能特點

1. **智慧批次處理**
   - 自動掃描 OTCQuote/TSEQuote 檔案
   - 根據漲停清單過濾，只保存相關股票
   - 大幅節省儲存空間（只保存當日+前一日漲停股票）

2. **網頁視覺化介面**
   - 即時走勢圖（價格 + 成交量）
   - 五檔報價顯示
   - 成交明細列表
   - 掛單變化歷史

3. **高效能資料處理**
   - Parquet 格式儲存
   - 快速查詢與載入
   - 支援大量歷史資料

## 檔案結構

```
.
├── batch_process.py          # 批次處理主程式
├── web_viewer.py             # Flask 網頁伺服器
├── requirements.txt          # Python 套件依賴
├── run_batch.bat            # 批次處理執行腳本
├── run_viewer.bat           # 網頁伺服器執行腳本
├── templates/
│   └── viewer.html          # 網頁模板
├── static/
│   ├── css/
│   │   └── style.css       # 樣式表
│   └── js/
│       └── chart.js        # 圖表邏輯
├── lup_ma20_filtered.parquet # 漲停股票清單
├── OTCQuote.YYYYMMDD        # 櫃買逐筆資料（輸入）
├── TSEQuote.YYYYMMDD        # 證交所逐筆資料（輸入）
└── processed_data/          # 處理後資料（輸出）
    └── YYYYMMDD/
        ├── 股票代碼1.parquet
        ├── 股票代碼2.parquet
        └── ...
```

## 安裝步驟

### 1. 建立 Conda 環境

```bash
conda create -n my_project python=3.10
conda activate my_project
```

### 2. 安裝套件

```bash
pip install -r requirements.txt
```

或手動安裝：

```bash
pip install pandas pyarrow flask numpy
```

## 使用方法

### 批次處理資料

**方法一：使用批次腳本（推薦）**

直接雙擊執行：
```
run_batch.bat
```

**方法二：手動執行**

```bash
conda activate my_project
python batch_process.py
```

**處理流程：**
1. 讀取 `lup_ma20_filtered.parquet` 漲停清單
2. 掃描目錄中的所有 Quote 檔案
3. 對每個日期，只保存當日+前一日漲停股票的資料
4. 輸出到 `processed_data/YYYYMMDD/` 目錄

### 啟動網頁視覺化

**方法一：使用批次腳本（推薦）**

直接雙擊執行：
```
run_viewer.bat
```

**方法二：手動執行**

```bash
conda activate my_project
python web_viewer.py
```

然後開啟瀏覽器訪問：
```
http://localhost:5000
```

## 網頁介面使用

1. **選擇日期**：從下拉選單選擇要查看的日期
2. **選擇股票**：從下拉選單選擇要查看的股票
3. **查看資料**：
   - 左側顯示價格走勢圖和成交量圖
   - 右上角顯示五檔報價
   - 右下角顯示成交明細
4. **互動功能**：
   - **點擊價格圖表**：自動滾動到對應時間的成交明細，並高亮顯示該行，同時更新五檔報價
   - **點擊成交明細**：在價格圖表上顯示紅色高亮點
   - **滾動成交明細**：五檔報價會即時跟隨更新，顯示當前瀏覽位置的五檔狀態
   - **時間軸滑桿**：拖動滑桿可以查看任意時間點的成交明細和五檔狀態
   - **自動播放**：點擊播放按鈕可以自動回放交易過程，支援多種速度（0.5x ~ 10x）
   - 五檔標題會顯示當前時間戳記（藍色字體）
   - 高亮效果會持續 3 秒後自動消失
5. **載入掛單歷史**：點擊「載入歷史」按鈕查看掛單變化

## 資料格式說明

### 輸入檔案

**OTCQuote/TSEQuote 格式：**
- Trade: `Trade,股票代碼,時間戳,Flag,價格,數量,總量`
- Depth: `Depth,股票代碼,時間戳,BID:count,買1~5,ASK:count,賣1~5`

**漲停清單格式：**
- 欄位：`date, stock_id, close_price, limit_up_price`

### 輸出檔案

Parquet 格式，包含以下欄位：

**Trade 資料：**
- Type, StockCode, Timestamp, Datetime
- Flag, Price, Volume, TotalVolume

**Depth 資料：**
- Type, StockCode, Timestamp, Datetime
- BidCount, Bid1_Price, Bid1_Volume, ..., Bid5_Volume
- AskCount, Ask1_Price, Ask1_Volume, ..., Ask5_Volume

## API 端點

系統提供以下 REST API：

- `GET /api/dates` - 獲取所有可用日期
- `GET /api/stocks/<date>` - 獲取指定日期的股票列表
- `GET /api/data/<date>/<stock_code>` - 獲取股票完整資料
- `GET /api/depth_history/<date>/<stock_code>` - 獲取五檔歷史變化

## 注意事項

1. **資料檔案位置**：
   - Quote 檔案需放在與程式相同的目錄
   - 漲停清單檔案 `lup_ma20_filtered.parquet` 需在同目錄

2. **Conda 環境**：
   - 確保已建立 `my_project` 環境
   - 如需使用不同環境名稱，請修改 bat 檔案

3. **效能優化**：
   - 只保存必要的股票資料，節省空間
   - 使用 Parquet 格式提升讀寫效能

4. **網頁瀏覽器**：
   - 建議使用 Chrome、Firefox 或 Edge
   - 需支援 JavaScript 和 Chart.js

## 疑難排解

**問題：找不到 conda 命令**
- 確認已安裝 Anaconda 或 Miniconda
- 確認 conda 已加入系統 PATH

**問題：無法啟動 my_project 環境**
- 執行 `conda env list` 檢查環境是否存在
- 如不存在，請先建立環境

**問題：批次處理沒有輸出**
- 檢查是否有 Quote 檔案在目錄中
- 檢查漲停清單是否有對應日期的資料
- 查看控制台的錯誤訊息

**問題：網頁顯示「暫無資料」**
- 確認已執行批次處理
- 確認 `processed_data/` 目錄中有資料
- 選擇有資料的日期和股票

## 授權

此專案為內部使用工具。

## 聯絡方式

如有問題或建議，請聯繫開發團隊。
