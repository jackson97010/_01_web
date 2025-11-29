# GitHub 上傳完整指南

## 📋 目錄

1. [問題分析](#問題分析)
2. [解決方案](#解決方案)
3. [上傳前準備](#上傳前準備)
4. [清理 Git 歷史](#清理-git-歷史)
5. [上傳步驟](#上傳步驟)
6. [常見問題](#常見問題)

---

## 🔍 問題分析

### 目前專案大小

```
總大小: ~44GB
├── data/         36GB  ❌ 太大，不應上傳
├── api/          6.9GB ❌ 太大，不應上傳
├── frontend-app/ 2.1GB ⚠️  包含 node_modules (180MB) 和 target (1.9GB)
├── rust/         1.1GB ⚠️  包含 target 編譯產物 (1.1GB)
└── 其他          ~2GB  ✅ 原始碼，應該上傳
```

### GitHub 限制

- 單個檔案最大: **100MB**
- Repository 建議大小: **< 1GB**
- 超過會有警告，超過 5GB 可能無法推送

### 需要排除的內容

#### 🚫 絕對不能上傳（資料檔案）
- `data/` - 36GB 原始資料
- `api/` - 6.9GB JSON 資料
- `*.parquet` - Parquet 資料檔案
- `OTCQuote.*` / `TSEQuote.*` - 原始 Quote 檔案

#### 🚫 編譯產物（可重新建置）
- `rust/target/` - Rust 編譯產物
- `frontend-app/src-tauri/target/` - Tauri 編譯產物
- `frontend-app/node_modules/` - Node.js 依賴
- `frontend-app/dist/` - 前端建置產物

#### ✅ 應該上傳（原始碼）
- `rust/src/` - Rust 原始碼
- `rust/Cargo.toml` - Rust 專案設定
- `frontend-app/src/` - 前端原始碼
- `scripts/` - Python 腳本
- `README.md` - 文檔

---

## 💡 解決方案

### 方案 A: 清理後上傳（推薦）⭐

**優點**:
- Repository 小巧（< 100MB）
- 上傳快速
- Clone 快速
- 符合 GitHub 最佳實踐

**缺點**:
- 協作者需要自行準備資料
- 需要清理 Git 歷史

### 方案 B: 使用 Git LFS

**優點**:
- 可以上傳大檔案
- Git 歷史乾淨

**缺點**:
- 需要額外設定
- GitHub LFS 有儲存限制（免費版 1GB/月）
- 對於 36GB+ 的資料不實際

### 方案 C: 分開儲存

**優點**:
- 程式碼在 GitHub
- 資料在其他地方（Google Drive、OneDrive、S3）

**缺點**:
- 需要維護多個位置
- 協作者需要額外步驟

---

## 🛠️ 上傳前準備

### 1. 檢查 .gitignore

您的 `.gitignore` 已經更新為：

```gitignore
# 大型資料檔案
data/
api/
*.parquet
OTCQuote.*
TSEQuote.*

# 編譯產物
rust/target/
frontend-app/src-tauri/target/
frontend-app/node_modules/
frontend-app/dist/

# IDE
.claude/
.vscode/
```

✅ **已完成！**

### 2. 確認要上傳的檔案

檢查哪些檔案會被上傳：

```bash
cd C:\Users\User\Documents\_web\_01_web

# 查看所有未被忽略的檔案
git status

# 或使用
git ls-files
```

預期大小應該 **< 100MB**

### 3. 移除敏感資訊

檢查是否有：
- API 金鑰
- 密碼
- 個人資料
- 敏感的設定檔

```bash
# 搜尋可能的敏感資訊
grep -r "password" .
grep -r "api_key" .
grep -r "secret" .
```

---

## 🧹 清理 Git 歷史

### 為什麼需要清理？

從 git log 可以看到之前有提交過大檔案：
- `lup_ma20_filtered.parquet` 已被刪除但仍在歷史中
- 可能有其他大檔案在歷史中

### 選項 1: 重新開始（最簡單）⭐

完全重置 Git 歷史，只保留目前的檔案：

```bash
cd C:\Users\User\Documents\_web\_01_web

# 1. 備份目前的 .git 目錄（以防萬一）
mv .git .git.backup

# 2. 重新初始化 Git
git init

# 3. 加入所有檔案（會自動遵守 .gitignore）
git add .

# 4. 檢查要提交的檔案大小
git ls-files | xargs ls -lh | awk '{sum+=$5} END {print "Total size:", sum/1024/1024, "MB"}'

# 5. 建立全新的初始 commit
git commit -m "Initial commit: 台股即時報價回放系統

- React 18 + TypeScript 前端
- Rust 高效能資料處理
- Python 資料解碼腳本
- 統一時間軸架構
- 排除大型資料檔案 (data/, api/)"
```

### 選項 2: 使用 git filter-repo（保留歷史）

如果想保留一些 commit 歷史：

```bash
# 1. 安裝 git-filter-repo
pip install git-filter-repo

# 2. 移除特定大檔案
git filter-repo --path data/ --invert-paths
git filter-repo --path api/ --invert-paths
git filter-repo --path lup_ma20_filtered.parquet --invert-paths

# 3. 強制垃圾回收
git gc --aggressive --prune=now
```

### 選項 3: 使用 BFG Repo-Cleaner

```bash
# 1. 下載 BFG
# https://rtyley.github.io/bfg-repo-cleaner/

# 2. 移除大於 10MB 的檔案
java -jar bfg.jar --strip-blobs-bigger-than 10M .

# 3. 清理
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

---

## 🚀 上傳步驟

### 步驟 1: 在 GitHub 建立 Repository

1. 登入 GitHub
2. 點擊右上角 `+` → `New repository`
3. 填寫資訊：
   - **Repository name**: `stock-quote-playback` 或您喜歡的名稱
   - **Description**: `台股即時報價回放系統 - React + Rust 高效能視覺化`
   - **Visibility**: Public 或 Private
   - **不要**勾選 "Initialize with README"（我們已有 README）
4. 點擊 `Create repository`

### 步驟 2: 連接到 GitHub

```bash
cd C:\Users\User\Documents\_web\_01_web

# 設定遠端 repository（替換成您的 GitHub 使用者名稱）
git remote add origin https://github.com/YOUR_USERNAME/stock-quote-playback.git

# 確認遠端連接
git remote -v
```

### 步驟 3: 推送到 GitHub

```bash
# 首次推送（建立 main 分支）
git push -u origin main

# 如果出現錯誤，可能需要先拉取
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### 步驟 4: 驗證上傳

1. 訪問您的 GitHub repository
2. 確認檔案都已上傳
3. 檢查 README.md 是否正確顯示
4. 查看 repository 大小（應該 < 100MB）

---

## 📦 建議的 Repository 結構

上傳到 GitHub 後，您的 repository 應該包含：

```
stock-quote-playback/
├── .gitignore                 ✅ 排除大檔案
├── README.md                  ✅ 專案說明
├── GITHUB_UPLOAD_GUIDE.md     ✅ 本指南
│
├── frontend-app/              ✅ 前端原始碼
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
│
├── rust/                      ✅ Rust 原始碼
│   ├── src/
│   ├── Cargo.toml
│   └── README.md
│
├── server/                    ✅ 後端原始碼
│   ├── nodejs/
│   └── python/
│
├── scripts/                   ✅ Python 腳本
│   ├── decode_quotes_correct.py
│   ├── batch_decode_quotes.py
│   └── README_DECODE.md
│
└── docs/                      ✅ 文檔
    └── screenshots/
```

**不會包含**（已在 .gitignore）:
- ❌ `data/` - 資料檔案
- ❌ `api/` - JSON API
- ❌ `rust/target/` - 編譯產物
- ❌ `node_modules/` - NPM 依賴

---

## 📝 建立 DATA_README.md

為了讓協作者知道如何準備資料，建議建立一個說明檔：

```bash
# 建立資料說明檔
cat > DATA_README.md << 'EOF'
# 資料準備指南

本專案不包含資料檔案（已在 .gitignore 排除）。

## 資料來源

您需要準備以下資料：

### 1. 原始 Quote 檔案
- `OTCQuote.YYYYMMDD` - 櫃買市場資料
- `TSEQuote.YYYYMMDD` - 上市市場資料

放置於 `data/` 目錄

### 2. 處理資料

執行解碼和轉換：

\`\`\`bash
# 解碼 Quote 檔案
python scripts/batch_decode_quotes.py

# 轉換成 JSON（可選）
python scripts/convert_to_json.py
\`\`\`

## 目錄結構

\`\`\`
data/
├── OTCQuote.20251031
├── TSEQuote.20251031
├── decoded_quotes/
│   └── 20251031/
│       └── *.parquet
└── lup_ma20_filtered.parquet

api/  # 或 frontend/static/api/
└── 20251031/
    └── *.json
\`\`\`

## 注意事項

- 資料檔案總大小約 40GB+
- 建議準備至少 50GB 可用空間
- 處理時間視資料量而定
EOF
```

---

## ❓ 常見問題

### Q1: 推送時顯示 "file too large"

**原因**: 有檔案超過 100MB
**解決**:
```bash
# 找出大檔案
find . -type f -size +10M | grep -v ".git"

# 確保這些檔案在 .gitignore 中
# 重新 commit
```

### Q2: 推送很慢或失敗

**原因**: Repository 太大
**解決**:
```bash
# 檢查 repository 大小
du -sh .git

# 如果 > 500MB，考慮清理歷史
git gc --aggressive --prune=now
```

### Q3: 協作者 clone 後無法運行

**原因**: 缺少資料檔案
**解決**: 提供 DATA_README.md 說明如何準備資料

### Q4: 如何更新 .gitignore

如果之前已經提交了不該提交的檔案：

```bash
# 1. 從 Git 中移除（但保留本地檔案）
git rm --cached -r data/
git rm --cached -r api/

# 2. 確認 .gitignore 包含這些路徑

# 3. 提交變更
git commit -m "Remove large data files from Git"

# 4. 推送
git push
```

### Q5: 如何分享資料給協作者？

選項：
1. **Google Drive / OneDrive**: 共享資料資料夾連結
2. **AWS S3 / Azure Blob**: 雲端儲存（付費）
3. **直接傳輸**: 如果是小團隊，可以直接分享

---

## 🎯 上傳檢查清單

### 準備階段
- [ ] 更新 .gitignore
- [ ] 清理 Git 歷史（如需要）
- [ ] 檢查無敏感資訊
- [ ] 確認 README.md 完整
- [ ] 建立 DATA_README.md

### 上傳階段
- [ ] 在 GitHub 建立 repository
- [ ] 連接遠端 repository
- [ ] 推送程式碼
- [ ] 驗證檔案正確

### 完成後
- [ ] 更新 README 中的 clone 指令
- [ ] 新增 topics/tags (React, TypeScript, Rust, Trading)
- [ ] 設定 GitHub Pages（如需要）
- [ ] 新增 LICENSE 檔案

---

## 📊 預期結果

上傳成功後：

✅ Repository 大小: **< 100MB**
✅ 包含所有原始碼
✅ 文檔完整
✅ 其他開發者可以 clone 並建置
✅ 資料檔案不在 repository 中

---

## 🔗 參考資源

- [GitHub 大檔案處理指南](https://docs.github.com/en/repositories/working-with-files/managing-large-files)
- [Git Filter-Repo](https://github.com/newren/git-filter-repo)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [Git LFS](https://git-lfs.github.com/)

---

**準備好了嗎？開始上傳吧！** 🚀
