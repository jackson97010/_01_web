# Server 後端伺服器

提供 API 服務，支援 Node.js 和 Python 兩種實作。

## 📁 結構

```
server/
├── nodejs/                  # Node.js/TypeScript 伺服器 ⭐ 推薦
│   ├── src/server.ts        # Express.js 主程式
│   ├── package.json         # 依賴管理
│   └── tsconfig.json        # TypeScript 設定
│
└── python/                  # Python 伺服器（備用）
    ├── parquet_server.py    # Parquet 即時轉換伺服器 ⭐ 節省空間
    └── static_server.py     # 靜態檔案伺服器
```

## 🚀 使用方式

### 方案 A：Node.js 伺服器（推薦）

```bash
cd server/nodejs

# 安裝依賴
npm install

# 開發模式（熱重載）
npm run dev

# 生產模式
npm run build
npm start
```

**特點**：
- ⚡ 高性能
- 🔄 TypeScript 熱重載
- 📦 gzip 壓縮
- 🌐 CORS 支援

### 方案 B：Python Parquet Server（節省空間）

```bash
cd server/python
python parquet_server.py --port 5000
```

**特點**：
- 💾 無需預先轉換 JSON
- 📉 節省 80-90% 儲存空間
- ⚡ 即時從 Parquet 轉換

### 方案 C：Python 靜態 Server（簡單）

```bash
cd server/python
python static_server.py --port 5000
```

**特點**：
- 🔌 簡單的靜態檔案服務
- 📁 需要預先執行 `convert_to_json.py`

## 📡 API 端點

所有伺服器都提供相同的 API：

```
GET /api/dates
回應：["20251112", "20251111", ...]

GET /api/stocks/{date}
回應：["2330", "2317", ...]

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

## 🔧 設定

### Node.js Server

預設 port: 5000，可在 `src/server.ts` 修改。

### Python Server

使用命令列參數：

```bash
# 指定 port
python parquet_server.py --port 8080

# 指定資料目錄
python parquet_server.py --data-dir /path/to/data
```

## 📦 依賴

### Node.js
```bash
npm install express cors compression
```

### Python
```bash
pip install pandas pyarrow flask
```

## 💡 選擇建議

| 情境 | 推薦方案 |
|------|---------|
| 開發測試 | Node.js Server |
| 生產環境 | Node.js Server |
| 儲存空間有限 | Python Parquet Server |
| 快速啟動 | Python Static Server |
