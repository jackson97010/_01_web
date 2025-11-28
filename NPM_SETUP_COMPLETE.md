# NPM 前後端設定完成

## ✅ 檢查結果

您的 frontend-app 和 server/nodejs 配置**完全正確，無需修改**！

### 前端 (frontend-app)
- ✅ React + TypeScript + Vite
- ✅ Port 3000
- ✅ API Proxy 正確設定（自動轉發到 localhost:5000）
- ✅ 環境變數支援（VITE_API_URL）
- ✅ 所有依賴齊全

### 後端 (server/nodejs)
- ✅ Express + TypeScript
- ✅ Port 5000
- ✅ API 路徑正確（/api/dates, /api/stocks, /api/data）
- ✅ CORS 已啟用
- ✅ Compression 已啟用

---

## 🚀 立即開始

### 最簡單的方式（推薦）

**Windows 用戶**，直接雙擊執行：

**選項 1：使用 Node.js 後端**
```
start-dev.bat
```

**選項 2：使用 Python Parquet Server（節省空間）**
```
start-parquet.bat
```

腳本會自動完成所有工作並開啟瀏覽器！

### 手動啟動

**首次使用**：
```bash
# 1. 轉換資料
python scripts\convert_to_json.py

# 2. 安裝前端依賴
cd frontend-app
npm install

# 3. 安裝後端依賴
cd ..\server\nodejs
npm install
```

**日常開發**：

開啟兩個終端機視窗：

**終端機 1：後端**
```bash
cd server\nodejs
npm run dev
```
→ 後端啟動在 http://localhost:5000

**終端機 2：前端**
```bash
cd frontend-app
npm run dev
```
→ 前端啟動在 http://localhost:3000

**瀏覽器**：
```
http://localhost:3000
```

---

## 📁 新增的檔案

```
✨ 新增：
├── start-dev.bat              # 一鍵啟動腳本（Node.js）
├── start-parquet.bat          # 一鍵啟動腳本（Python Parquet）
├── NPM_GUIDE.md              # 完整 npm 使用指南
├── NPM_SETUP_COMPLETE.md     # 本文件
└── README.md                 # 已更新（加入新架構說明）

📝 文件：
├── DECODE_SUMMARY.md         # 解碼任務總結
├── ARCHITECTURE_UPDATE.md    # 架構更新說明
├── USAGE_GUIDE.md           # 詳細使用指南
├── MIGRATION_COMPLETE.md    # 遷移完成報告
└── scripts/README_DECODE.md # 解碼規格
```

---

## 📖 配置詳情

### 前端配置

**vite.config.ts**（無需修改）：
```typescript
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
```

**API 服務**（無需修改）：
```typescript
// src/services/api.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
```

### 後端配置

**server.ts**（無需修改）：
```typescript
const PORT = process.env.PORT || 5000;
const apiDataPath = path.join(__dirname, '../../../frontend/static/api');
```

---

## 🔄 工作流程

```
開發流程：
1. 解碼資料      → python scripts\batch_decode_quotes.py
2. 轉換 JSON     → python scripts\convert_to_json.py（可選）
3. 啟動後端      → npm run dev（在 server/nodejs）
4. 啟動前端      → npm run dev（在 frontend-app）
5. 開啟瀏覽器    → http://localhost:3000

API 調用流程：
前端 (localhost:3000)
  ↓ 請求 /api/dates
  ↓ Vite proxy 自動轉發
後端 (localhost:5000/api/dates)
  ↓ 讀取資料
  ↓ 回傳 JSON
前端接收並顯示
```

---

## 🎯 API 端點

所有 API 都已正確配置：

```http
GET /api/dates
→ 回應: ["20251031", "20251103", ...]

GET /api/stocks/:date
→ 回應: ["1503", "1514", "1519", ...]

GET /api/data/:date/:stock
→ 回應: { chart, depth, trades, stats, ... }
```

---

## 🛠️ NPM Scripts

### frontend-app
```bash
npm run dev      # 開發模式（http://localhost:3000）
npm run build    # 打包生產版本
npm run preview  # 預覽打包結果
```

### server/nodejs
```bash
npm run dev      # 開發模式（自動重啟）
npm run build    # 編譯 TypeScript
npm start        # 生產模式
npm run clean    # 清理編譯結果
```

---

## 📚 完整文件

詳細資訊請查看：

1. **NPM_GUIDE.md** ⭐ - npm 完整使用指南
   - 詳細的配置說明
   - 開發工具推薦
   - 效能優化建議
   - 故障排除

2. **README.md** - 專案總覽（已更新）
   - 專案介紹
   - 快速開始
   - 功能說明

3. **USAGE_GUIDE.md** - 使用指南
   - 兩種部署方案
   - API 使用說明
   - 常見問題

---

## ❓ 常見問題

### Q: 前端和後端配置需要修改嗎？
**A:** **不需要！** 所有配置都已正確，可以直接使用。

### Q: 我應該用哪種方式啟動？
**A:** 建議使用 `start-dev.bat` 最簡單。或者手動啟動兩個終端機。

### Q: 資料從哪裡來？
**A:**
1. 原始資料：`data/OTCQuote.*`, `data/TSEQuote.*`
2. 解碼後：`data/decoded_quotes/` (Parquet)
3. 轉換後：`frontend/static/api/` (JSON)

### Q: 需要預先轉換 JSON 嗎？
**A:**
- **使用 Node.js 後端**：需要（執行 `convert_to_json.py`）
- **使用 Python Parquet Server**：不需要（即時轉換）

### Q: 如何更新資料？
**A:**
```bash
# 1. 解碼新資料
python scripts\batch_decode_quotes.py

# 2. 如果使用 Node.js 後端，轉換為 JSON
python scripts\convert_to_json.py

# 3. 重啟 server（如果正在運行）
```

### Q: Port 衝突怎麼辦？
**A:**
- 前端：Vite 會自動選擇其他 port (3001, 3002...)
- 後端：修改 `server/nodejs/src/server.ts` 中的 `PORT`

---

## ✨ 總結

**所有配置都是正確的，您可以立即開始使用！**

**最快的開始方式**：
```bash
start-dev.bat
```

**就這麼簡單！** 🚀

---

**更新日期**：2025-11-20
**狀態**：✅ 配置檢查完成，無需修改
