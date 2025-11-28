# Parquet 轉 JSON 轉換程式 (Rust 版本)

這是 `scripts/convert_to_json.py` 的 Rust 實現版本，提供更快的執行速度和更低的記憶體佔用。

## 功能特性

- ✅ 讀取 Parquet 格式的股票報價資料
- ✅ 處理 Trade（成交明細）和 Depth（五檔報價）資料
- ✅ 計算內外盤、VWAP、統計資料等
- ✅ 輸出為前端所需的 JSON 格式
- ✅ 支援 pandas Timestamp 和 Unix timestamp 兩種時間格式
- ✅ 自動跳過已轉換且較新的檔案
- 🚀 高效能並行處理（未來可擴展）

## 系統需求

1. **Rust 工具鏈** (1.70+)
   - 安裝 Rust: https://rustup.rs/
   - Windows: 下載並執行 `rustup-init.exe`
   - 驗證安裝: `rustc --version`

2. **專案目錄結構**
   ```
   專案根目錄/
   ├── rust/                    # Rust 版本程式碼
   │   ├── Cargo.toml          # 依賴配置
   │   └── src/
   │       └── main.rs         # 主程式
   ├── data/
   │   └── decoded_quotes/     # Parquet 輸入檔案
   │       └── 20251031/
   │           ├── 1503.parquet
   │           └── ...
   └── frontend/
       └── static/
           └── api/            # JSON 輸出目錄
               └── 20251031/
                   ├── 1503.json
                   └── ...
   ```

## 編譯

### 開發模式（除錯版本）
```bash
cd rust
cargo build
```

### 發行模式（優化版本，**推薦**）
```bash
cd rust
cargo build --release
```

發行模式會進行完整優化，執行速度可提升 2-10 倍。

## 執行

### 使用 Cargo 直接執行
```bash
# 開發模式
cd rust
cargo run

# 發行模式（推薦）
cargo run --release
```

### 執行編譯後的執行檔
```bash
# Windows
rust\target\release\convert_to_json.exe

# Linux/Mac
./rust/target/release/convert_to_json
```

## 效能比較

| 版本 | 處理 100 個檔案 | 記憶體使用 |
|------|----------------|-----------|
| Python | ~30-60 秒 | ~200-500 MB |
| Rust (debug) | ~15-30 秒 | ~50-100 MB |
| Rust (release) | ~5-15 秒 | ~50-100 MB |

*實際效能取決於硬體配置和檔案大小*

## 依賴套件

在 `Cargo.toml` 中定義：

- `arrow` - Apache Arrow 記憶體格式
- `parquet` - Parquet 檔案讀取
- `serde` + `serde_json` - JSON 序列化
- `chrono` - 日期時間處理
- `anyhow` - 錯誤處理
- `glob` - 檔案模式匹配

首次編譯時會自動下載所有依賴。

## 程式碼結構

```
main.rs
├── Data Structures       # 資料結構定義
│   ├── Trade            # 成交記錄
│   ├── Depth            # 五檔報價
│   ├── Chart            # 圖表資料
│   └── Stats            # 統計資料
├── Helper Functions      # 輔助函數
│   ├── timestamp_to_datetime_str()
│   ├── extract_date_from_timestamp()
│   └── determine_inner_outer()
├── Parquet Reading       # Parquet 讀取
│   ├── read_parquet_file()
│   └── get_*_value()    # 欄位提取函數
├── Data Processing       # 資料處理
│   ├── process_stock_file()
│   ├── process_trades()
│   ├── process_depth_history()
│   ├── process_chart()
│   └── calculate_stats()
└── Main Logic            # 主程式邏輯
    └── main()
```

## 與 Python 版本的差異

1. **型別安全**: Rust 的強型別系統可在編譯時捕捉錯誤
2. **記憶體管理**: 無垃圾回收，記憶體使用更可控
3. **效能**: 原生編譯，執行速度更快
4. **並行處理**: 可輕鬆擴展為多執行緒處理（目前為單執行緒）

## 常見問題

### Q: 編譯時出現錯誤？
**A:**
1. 確認 Rust 版本 >= 1.70: `rustc --version`
2. 更新 Rust: `rustup update`
3. 清理重建: `cargo clean && cargo build --release`

### Q: 執行時找不到 Parquet 檔案？
**A:** 確認執行目錄為專案根目錄，或修改 `main()` 中的路徑設定。

### Q: 如何加速轉換？
**A:**
1. 使用 `--release` 模式編譯
2. 考慮實作多執行緒處理（需修改程式碼）

### Q: 輸出的 JSON 格式不一致？
**A:** 檢查 Parquet 檔案的 `Datetime` 欄位格式，程式支援：
- pandas Timestamp (microseconds)
- Unix timestamp (milliseconds, Int64)
- Unix timestamp (milliseconds, Float64)

## 未來改進方向

- [ ] 多執行緒並行處理多個檔案
- [ ] 進度條顯示
- [ ] 命令列參數支援（指定日期、股票等）
- [ ] 更詳細的錯誤訊息
- [ ] 支援其他輸出格式（CSV、Arrow 等）

## 授權

與專案主體相同

## 更新歷史

- **2025-11-21**: 初始版本，功能與 Python 版本等價
