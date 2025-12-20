# 台股極速回放系統 Pro Max - Electron 版

## 功能特色

✅ **五檔報價顯示**
- 實時顯示買賣五檔價格與量
- 量能變化視覺化（能量條）
- 委買委賣量變動 Diff 提示

✅ **成交資訊**
- 大字顯示最新成交價
- 內外盤判斷與標記
- 成交量統計

✅ **走勢圖（NEW！）**
- 分時價格走勢圖
- 成交量柱狀圖
- 內外盤顏色區分
- 從 09:00 開始顯示
- 隨播放進度動態更新

✅ **播放控制**
- 自動播放/暫停
- 上一筆/下一筆
- 時間軸拖曳
- 微秒級時間跳轉
- 鍵盤快捷鍵（←/→）

✅ **數據支援**
- Parquet 文件讀取
- JSON 文件讀取
- 文件選擇對話框

## 安裝與運行

### 1. 安裝依賴

```bash
npm install
```

### 2. 開發模式運行

```bash
npm run dev
```

這會同時啟動：
- Vite 開發服務器（端口 5173）
- Electron 桌面應用

### 3. 生產模式運行

```bash
# 先構建前端
npm run build

# 啟動 Electron
npm start
```

## 使用說明

### 載入數據

1. 在文件路徑輸入框中輸入數據文件路徑，或點擊「選檔」按鈕選擇文件
2. 點擊「重新載入」按鈕載入數據
3. 支援的格式：`.parquet`、`.json`

### 播放控制

- **播放/暫停**：點擊中央的播放按鈕
- **上一筆/下一筆**：點擊對應按鈕或使用鍵盤 ← →
- **拖曳時間軸**：滑動時間軸可快速跳轉
- **時間跳轉**：輸入時間（格式：HH:MM:SS.ffffff）並點擊「跳到時間」

### 查看走勢圖

- 走勢圖會自動顯示從 09:00 開始的成交數據
- 上方為價格走勢線，下方為成交量柱狀圖
- 紅色代表外盤，綠色代表內盤
- 滑鼠懸停可查看詳細資訊
- 圖表會隨播放進度實時更新

## 技術棧

- **框架**: Electron + React + TypeScript
- **構建工具**: Vite
- **圖表庫**: ECharts
- **數據處理**: parquetjs-lite
- **樣式**: CSS Variables

## 項目結構

```
app/
├── electron/           # Electron 主進程
│   ├── main.js        # 主進程入口
│   └── preload.js     # 預加載腳本
├── src/               # React 應用源碼
│   ├── components/    # React 組件
│   │   └── PriceChart.tsx  # 走勢圖組件
│   ├── utils/         # 工具函數
│   │   └── replay.ts  # 回放數據處理
│   ├── App.tsx        # 主應用組件
│   ├── main.tsx       # React 入口
│   ├── styles.css     # 全局樣式
│   └── types.ts       # TypeScript 類型定義
├── package.json       # 項目配置
└── vite.config.ts     # Vite 配置
```

## 數據格式要求

### Parquet/JSON 文件結構

```json
[
  {
    "Type": "Depth",
    "Timestamp": 90000123456,
    "Datetime": "2024-12-19T09:00:00.123456",
    "Bid1_Price": 34.50,
    "Bid1_Volume": 100,
    "Ask1_Price": 34.55,
    "Ask1_Volume": 150,
    ...
  },
  {
    "Type": "Trade",
    "Timestamp": 90000234567,
    "Datetime": "2024-12-19T09:00:00.234567",
    "Price": 34.55,
    "Volume": 10,
    "BS_Flag": "Out"
  }
]
```

### 必要欄位

- `Type`: "Depth" 或 "Trade"
- `Timestamp`: 微秒時間戳（數字）
- `Datetime`: 日期時間字串或 Date 對象
- 五檔數據（Depth）：`Bid1_Price`, `Bid1_Volume`, `Ask1_Price`, `Ask1_Volume` 等
- 成交數據（Trade）：`Price`, `Volume`, `BS_Flag`

## 快捷鍵

- `←` 左箭頭：上一筆
- `→` 右箭頭：下一筆

## 開發者說明

### 添加新功能

1. 在 `src/components/` 創建新組件
2. 在 `src/App.tsx` 中引入並使用
3. 在 `src/styles.css` 添加樣式

### 修改圖表

編輯 `src/components/PriceChart.tsx`，參考 [ECharts 文檔](https://echarts.apache.org/zh/index.html)

### 打包發佈

```bash
# 安裝 electron-builder
npm install --save-dev electron-builder

# 打包
npx electron-builder
```

## 問題排查

### 1. 圖表不顯示

- 確認數據已正確載入
- 檢查瀏覽器控制台是否有錯誤
- 確認數據中有 Trade 類型的記錄

### 2. 文件載入失敗

- 檢查文件路徑是否正確
- 確認文件格式符合要求
- 查看 Electron 控制台錯誤訊息

### 3. 播放卡頓

- 減少數據量或使用過濾
- 調整播放速度（修改 `setInterval` 延遲時間）

## 更新日誌

### v1.1.0 (2024-12-20)
- ✨ 新增走勢圖功能
- ✨ 新增成交量柱狀圖
- 🎨 優化界面佈局
- 🐛 修復若干 bug

### v1.0.0
- 🎉 初始版本發佈
- ✅ 五檔報價顯示
- ✅ 播放控制功能
- ✅ Parquet/JSON 文件支援

## 授權

MIT License

---

**開發者**: Claude Code
**最後更新**: 2024-12-20
