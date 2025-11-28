# 程式碼優化計劃

> 📅 **建立日期**: 2025-11-28
> 🎯 **目標**: 全面檢查和優化專案，使其更簡潔、專業、易維護

---

## 📊 現狀分析

### 發現的問題

#### 1. **Python 腳本重複**
```
scripts/
├── batch_process.py (15K) ❌ 舊版
├── batch_decode_quotes.py (13K) ⚠️ 可能重複
├── decode_quotes.py (11K) ⚠️ 可能重複
├── decode_quotes_correct.py (14K) ✅ 最新版本
├── test_decode_both.py (4.4K) ⚠️ 可合併
├── test_decode_single.py (3.9K) ⚠️ 可合併
└── verify_decode.py (6.6K) ⚠️ 可合併
```

**問題**:
- 多個解碼腳本功能重疊
- 測試腳本分散
- 命名不一致

#### 2. **文檔過多且重複**
```
根目錄:
├── ARCHITECTURE_UPDATE.md (7.9K)
├── DECODE_SUMMARY.md (5.2K)
├── GITHUB_UPLOAD_GUIDE.md (10.5K)
├── MIGRATION_COMPLETE.md (8.5K)
├── NPM_GUIDE.md (9.8K)
├── NPM_SETUP_COMPLETE.md (5.8K)
├── UPLOAD_SUMMARY.md (7.8K)
├── USAGE_GUIDE.md (7.6K)
├── DATA_README.md (6.3K)
└── claude.md (6.0K)
```

**問題**:
- 11個 MD 檔案，內容重複
- 沒有清晰的文檔層次
- 部分文檔已過時

#### 3. **目錄結構問題**
```
根目錄混亂:
├── test.py
├── test_decode.py
├── run-rust-convert.bat
├── clean_git_history.bat
├── upload_to_github.bat
└── start-*.bat
```

**問題**:
- 臨時檔案和工具混在根目錄
- 沒有統一的工具目錄

---

## 🎯 優化目標

### 1. **程式碼優化**
- ✅ 統一使用最佳實踐
- ✅ 移除重複程式碼
- ✅ 改善錯誤處理
- ✅ 添加完整的型別提示（Python）
- ✅ 優化效能

### 2. **結構優化**
- ✅ 清晰的目錄層次
- ✅ 統一的命名規範
- ✅ 分離關注點（開發/測試/文檔）

### 3. **文檔優化**
- ✅ 合併重複內容
- ✅ 建立清晰的導覽
- ✅ 保持簡潔精確

---

## 📋 優化方案

### 階段 1: Python 腳本整合

#### 保留和重命名
```
scripts/
├── decode.py ✅ (decode_quotes_correct.py 重命名)
├── batch_decode.py ✅ (batch_decode_quotes.py 簡化)
├── convert_json.py ✅ (convert_to_json.py 重命名)
├── query_stock.py ✅ (get_single_stock_data.py 重命名)
└── tests/
    ├── test_decode.py ✅ (合併所有測試)
    └── verify.py ✅ (verify_decode.py 簡化)
```

#### 移除
- ❌ `batch_process.py` (舊版)
- ❌ `decode_quotes.py` (舊版)
- ❌ `test_decode_single.py` (合併到 test_decode.py)
- ❌ `test_decode_both.py` (合併到 test_decode.py)

### 階段 2: 文檔整理

#### 保留結構
```
docs/
├── README.md ✅ 主文檔（保留根目錄）
├── SETUP.md ✅ 安裝設定（合併 NPM_GUIDE, NPM_SETUP_COMPLETE）
├── DATA_GUIDE.md ✅ 資料處理（合併 DATA_README, DECODE_SUMMARY）
├── DEVELOPMENT.md ✅ 開發指南（合併 ARCHITECTURE_UPDATE, MIGRATION_COMPLETE）
└── CONTRIBUTING.md ✅ 貢獻指南（新建，包含 Git workflow）
```

#### 移除
- ❌ `GITHUB_UPLOAD_GUIDE.md` (整合到 CONTRIBUTING.md)
- ❌ `UPLOAD_SUMMARY.md` (整合到 CONTRIBUTING.md)
- ❌ `USAGE_GUIDE.md` (整合到 README.md)
- ❌ `claude.md` (移到 .claude/)

### 階段 3: 目錄結構優化

#### 新結構
```
_01_web/
├── docs/               ✅ 所有文檔
├── scripts/            ✅ 資料處理腳本
│   ├── decode.py
│   ├── batch_decode.py
│   ├── convert_json.py
│   ├── query_stock.py
│   └── tests/
├── tools/              ✅ 開發工具
│   ├── clean_git.bat
│   ├── start_dev.bat
│   └── start_parquet.bat
├── rust/               ✅ Rust 專案
├── server/             ✅ 後端伺服器
├── frontend-app/       ✅ 前端應用
└── README.md           ✅ 主入口
```

### 階段 4: Rust 優化

#### 改進重點
```rust
// 1. 錯誤處理改進
Result<T, Error> with proper error types

// 2. 性能優化
- 使用 rayon 並行處理
- 減少記憶體複製
- 優化序列化

// 3. 程式碼組織
- 分離模組
- 添加單元測試
- 改善文檔註釋
```

---

## 🔧 實施步驟

### Step 1: 備份
```bash
# 建立備份分支
git checkout -b pre-optimization-backup
git push origin pre-optimization-backup

# 回到 main
git checkout main
```

### Step 2: Python 腳本優化
1. 重命名和簡化主要腳本
2. 合併測試腳本
3. 移除舊版本
4. 更新導入和參考

### Step 3: 文檔整理
1. 建立 docs/ 目錄
2. 合併和重組內容
3. 更新所有連結
4. 移除重複檔案

### Step 4: 目錄結構
1. 建立 tools/ 目錄
2. 移動工具腳本
3. 清理根目錄
4. 更新路徑參考

### Step 5: Rust 優化
1. 重構程式碼結構
2. 改進錯誤處理
3. 添加測試
4. 優化效能

### Step 6: 提交和測試
1. 測試所有功能
2. 更新 README
3. 提交變更
4. 推送到 GitHub

---

## ✅ 預期成果

### 程式碼品質
- ✅ 移除 50% 重複程式碼
- ✅ 統一命名規範
- ✅ 完整的型別提示
- ✅ 更好的錯誤處理

### 專案結構
- ✅ 清晰的目錄層次
- ✅ 分離關注點
- ✅ 易於導航和維護

### 文檔
- ✅ 減少 60% 文檔檔案
- ✅ 清晰的文檔導覽
- ✅ 無重複內容

### 可維護性
- ✅ 更容易理解
- ✅ 更容易擴展
- ✅ 更容易除錯

---

## 📊 優化指標

| 項目 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| Python 腳本 | 10 個 | 6 個 | -40% |
| MD 文檔 | 11 個 | 5 個 | -55% |
| 根目錄檔案 | 20+ 個 | 10 個 | -50% |
| 程式碼重複 | 高 | 低 | -60% |
| 易維護性 | 中 | 高 | +100% |

---

## 🚀 開始優化

準備好了嗎？讓我們開始優化！

**執行順序**:
1. ✅ 建立備份
2. ⏳ Python 腳本優化
3. ⏳ 文檔整理
4. ⏳ 目錄結構優化
5. ⏳ Rust 優化
6. ⏳ 測試和提交

---

**目標**: 打造一個專業、簡潔、易維護的量化交易系統！ 🎯
