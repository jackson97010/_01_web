# 資料準備指南

> ⚠️ **重要**: 本專案不包含資料檔案（已在 .gitignore 排除）

資料檔案總大小約 **40GB+**，不適合上傳到 GitHub。

---

## 📁 需要的資料檔案

### 1. 原始 Quote 檔案

從證交所下載的原始資料：

```
data/
├── OTCQuote.20251031    # 櫃買市場 (341 MB)
├── OTCQuote.20251103    # 櫃買市場 (327 MB)
├── TSEQuote.20251031    # 上市市場 (1.0 GB)
└── TSEQuote.20251103    # 上市市場 (1.2 GB)
```

**總大小**: 約 36GB

### 2. 漲停股票清單

```
data/
└── lup_ma20_filtered.parquet    # 漲停股票清單 (212 KB)
```

**說明**: 包含歷史漲停股票的日期和代碼

---

## 🔧 資料處理流程

### 步驟 1: 準備原始資料

將 Quote 檔案和 parquet 檔案放入 `data/` 目錄：

```bash
data/
├── OTCQuote.*
├── TSEQuote.*
└── lup_ma20_filtered.parquet
```

### 步驟 2: 解碼 Quote 檔案

使用新版解碼程式（推薦）：

```bash
# 批次處理所有日期
python scripts/decode_quotes_correct.py

# 或測試單一日期
python scripts/test_decode_both.py
```

**輸出**:
```
data/decoded_quotes/
├── 20251031/
│   ├── 1503.parquet
│   ├── 1514.parquet
│   └── ...
└── 20251103/
    └── ...
```

**處理時間**:
- 單個日期: 約 10-30 秒
- 全部日期: 視資料量而定（支援多線程）

### 步驟 3: 轉換成 JSON（可選）

#### 選項 A: 使用 Parquet Server（推薦）⭐

不需要轉換，直接使用 Parquet 檔案：

```bash
cd server/python
python parquet_server.py --port 5000
```

**優點**:
- 即時轉換，無需預先處理
- 節省 80-90% 儲存空間
- 更新資料後立即可用

#### 選項 B: 轉換成靜態 JSON

如果需要靜態 JSON 檔案：

```bash
python scripts/convert_to_json.py
```

**輸出**:
```
api/  # 或 frontend/static/api/
├── 20251031/
│   ├── 1503.json (15 MB)
│   ├── 1514.json (12 MB)
│   └── ...
└── 20251103/
    └── ...
```

**總大小**: 約 6.9GB

---

## 📂 完整目錄結構

處理完成後的目錄結構：

```
_01_web/
│
├── data/                           # 原始和處理後的資料（不上傳 GitHub）
│   ├── OTCQuote.20251031           # 原始 OTC 資料
│   ├── TSEQuote.20251031           # 原始 TSE 資料
│   ├── lup_ma20_filtered.parquet   # 漲停清單
│   │
│   └── decoded_quotes/             # 解碼後的 Parquet
│       ├── 20251031/
│       │   ├── 1503.parquet
│       │   └── ...
│       └── 20251103/
│           └── ...
│
├── api/                            # JSON API 資料（可選，不上傳 GitHub）
│   ├── 20251031/
│   │   ├── 1503.json
│   │   └── ...
│   └── 20251103/
│       └── ...
│
└── scripts/                        # 處理腳本（上傳 GitHub）
    ├── decode_quotes_correct.py    # 解碼程式
    ├── convert_to_json.py          # JSON 轉換
    └── README_DECODE.md            # 解碼說明
```

---

## 💾 儲存空間需求

| 資料類型 | 大小 | 說明 |
|---------|------|------|
| 原始 Quote 檔案 | ~36GB | OTCQuote.* + TSEQuote.* |
| 解碼後 Parquet | ~5-10GB | decoded_quotes/ |
| JSON API 資料 | ~6.9GB | api/ (如果轉換) |
| **總計** | **~50GB** | 建議預留空間 |

**建議**: 如使用 Parquet Server，可省略 JSON 轉換，總空間需求降至 **~45GB**

---

## 🔍 資料來源

### 官方來源

- **證券交易所** (TSE): https://www.twse.com.tw/
- **櫃買中心** (OTC): https://www.tpex.org.tw/

### 資料格式

參考 `scripts/README_DECODE.md` 了解 Quote 檔案格式。

---

## 🤝 團隊協作

### 情境 1: 小團隊（推薦）

**方式**: 直接分享資料資料夾

```bash
# 成員 A 準備資料並壓縮
zip -r data.zip data/

# 分享給成員 B
# 成員 B 解壓縮到專案根目錄
unzip data.zip
```

### 情境 2: 遠端協作

**方式 A - 雲端硬碟**:
1. 上傳 `data/` 到 Google Drive / OneDrive
2. 分享連結給團隊成員
3. 成員下載並放到專案根目錄

**方式 B - 自建伺服器**:
1. 架設 FTP / HTTP 伺服器
2. 提供下載連結
3. 成員使用 wget / curl 下載

### 情境 3: 開源專案

如果是公開專案：

1. 在 README 說明資料來源和處理方式
2. 提供處理腳本
3. 不提供原始資料（讓使用者自行取得）

**範例說明**:
```markdown
## 資料準備

本專案不包含資料。請：

1. 從證交所下載 Quote 資料
2. 執行 `python scripts/decode_quotes_correct.py` 處理
3. 啟動服務
```

---

## 🔐 資料安全

### 注意事項

⚠️ **不要將資料上傳到公開的地方**，除非您有權限且符合授權條款

✅ **使用 .gitignore** 確保資料不會意外提交到 Git

✅ **定期備份** 處理後的資料，避免重新處理

### 確認資料已被忽略

```bash
# 檢查 Git 狀態
git status

# 應該不會看到 data/ 或 api/ 目錄
# 如果看到，確認 .gitignore 設定正確
```

---

## 🐛 常見問題

### Q1: 解碼失敗

**檢查**:
- Python 依賴是否安裝 (`pip install pandas pyarrow`)
- 原始檔案是否完整
- 漲停清單是否存在

**解決**:
```bash
# 重新安裝依賴
pip install --upgrade pandas pyarrow

# 測試單一檔案
python scripts/test_decode_both.py
```

### Q2: JSON 轉換太慢

**原因**: 資料量大

**解決**:
- 使用 Parquet Server（推薦）
- 或使用多線程版本（如果有）

### Q3: 空間不足

**解決**:
- 只處理需要的日期
- 處理完刪除原始 Quote 檔案
- 使用 Parquet Server 省略 JSON 轉換

---

## 📞 需要幫助？

如有資料處理問題：

1. 查看 `scripts/README_DECODE.md`
2. 查看 `scripts/DECODE_SUMMARY.md`
3. 開 GitHub Issue

---

**資料準備完成後，即可開始使用系統！** 🚀
