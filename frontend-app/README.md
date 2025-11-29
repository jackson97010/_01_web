# Frontend Application

React + TypeScript 前端應用，使用 Vite 建置。

## 📁 結構

```
frontend-app/
├── src/
│   ├── components/          # React 組件
│   │   ├── Header.tsx       # 頂部導航與選單
│   │   ├── StockChart.tsx   # 價格與成交量圖表
│   │   ├── DepthTable.tsx   # 五檔報價表
│   │   ├── TradeList.tsx    # 成交明細列表
│   │   └── TimelineControls.tsx # 時間軸控制器
│   │
│   ├── stores/              # Zustand 狀態管理
│   │   └── stockStore.ts    # 全域狀態（含統一時間軸）
│   │
│   ├── services/            # API 服務
│   │   └── api.ts           # HTTP 請求封裝
│   │
│   ├── types/               # TypeScript 型別定義
│   │   └── stock.ts         # 資料型別
│   │
│   └── styles/              # 樣式檔案
│       └── index.css        # TailwindCSS
│
├── package.json             # 依賴管理
├── vite.config.ts           # Vite 設定
└── tsconfig.json            # TypeScript 設定
```

## 🚀 開發

```bash
# 安裝依賴
npm install

# 啟動開發伺服器 (http://localhost:3000)
npm run dev

# 建置生產版本
npm run build

# 預覽生產版本
npm run preview
```

## 🖥️ Tauri 桌面應用（可選）

```bash
# 開發模式
npm run tauri:dev

# 建置桌面應用
npm run tauri:build
```

## 🎨 技術棧

- **React 18** - UI 框架
- **TypeScript 5** - 型別安全
- **Zustand** - 輕量狀態管理
- **Chart.js 4** - 圖表渲染
- **TailwindCSS 3** - 樣式框架
- **Vite** - 建置工具
- **Tauri 2.0** - 桌面應用（可選）

## 📡 API 設定

前端會自動連接到 `http://localhost:5000` 的後端 API。

Vite 已配置 proxy，所有 `/api/*` 請求會自動轉發到後端。

## 🔧 環境變數

可以在 `.env` 檔案中設定（可選）：

```env
VITE_API_URL=http://localhost:5000
```

## 📦 主要依賴

```json
{
  "react": "^18.3.1",
  "zustand": "^4.5.2",
  "chart.js": "^4.4.3",
  "axios": "^1.7.2",
  "tailwindcss": "^3.4.4"
}
```
