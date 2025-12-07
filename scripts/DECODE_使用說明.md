# decode.py 使用說明

## 功能概述
這個工具可以解碼 OTC/TSE Quote 檔案為 Parquet 格式，支援三種運作模式。

## 資料來源
- 資料目錄：`C:\Users\tacor\Documents\tick-data`
- 支援的檔案格式：`OTCQuote.YYYYMMDD` 和 `TSEQuote.YYYYMMDD`

## 使用方式

### 1. 批次模式（使用漲停清單）
自動處理漲停清單中的所有日期和股票：
```bash
python decode.py
```

### 2. 指定模式
透過命令行參數指定日期和股票代碼：

```bash
# 基本用法
python decode.py --date 20240101 --stocks 2330,2317

# 指定市場（僅處理 TSE）
python decode.py --date 20240101 --stocks 2330,2317 --market TSE

# 指定多支股票
python decode.py -d 20240101 -s 2330,2317,2454,2881,2882 -m BOTH

# 自訂輸出目錄
python decode.py -d 20240101 -s 2330 -o D:\output\quotes
```

### 3. 互動模式
透過互動式問答輸入參數：
```bash
python decode.py --interactive
# 或簡寫
python decode.py -i
```

執行後會依序詢問：
1. 日期（格式：YYYYMMDD，例如：20240101）
2. 股票代碼（多個股票用逗號分隔，例如：2330,2317,2454）
3. 市場選擇（TSE/OTC/BOTH，預設 BOTH）
4. 輸出目錄（可直接按 Enter 使用預設）

## 參數說明

| 參數 | 簡寫 | 說明 | 範例 |
|------|------|------|------|
| `--date` | `-d` | 指定日期（YYYYMMDD） | `20240101` |
| `--stocks` | `-s` | 股票代碼（逗號分隔） | `2330,2317` |
| `--market` | `-m` | 市場（TSE/OTC/BOTH） | `TSE` |
| `--output` | `-o` | 輸出目錄 | `D:\output` |
| `--interactive` | `-i` | 啟用互動模式 | - |
| `--help` | `-h` | 顯示說明 | - |

## 輸出格式

解碼後的檔案會儲存為：
```
輸出目錄/
└── YYYYMMDD/
    ├── 2330.parquet
    ├── 2317.parquet
    └── ...
```

每個 Parquet 檔案包含該股票當日的：
- 成交資料（Trade）
- 五檔報價資料（Depth）

## 使用範例

### 範例 1：解碼台積電（2330）2024年1月1日資料
```bash
python decode.py -d 20240101 -s 2330 -m TSE
```

### 範例 2：解碼多支金融股
```bash
python decode.py -d 20240101 -s 2881,2882,2883,2884,2885 -m TSE
```

### 範例 3：同時解碼 TSE 和 OTC 市場
```bash
python decode.py -d 20240101 -s 2330,6223,8040 -m BOTH
```

### 範例 4：使用互動模式（最簡單）
```bash
python decode.py -i
```
然後依照提示輸入：
```
請輸入日期 (YYYYMMDD，例如 20240101): 20240101
請輸入股票代碼（多個股票用逗號分隔，例如 2330,2317,2454): 2330,2317
請選擇市場 (TSE/OTC/BOTH，預設 BOTH): TSE
輸出目錄（預設 ...，直接按 Enter 使用預設）:
```

## 注意事項

1. **資料來源檔案必須存在**
   - 確保 `C:\Users\tacor\Documents\tick-data` 中有對應的 Quote 檔案
   - 檔案命名格式：`TSEQuote.20240101` 或 `OTCQuote.20240101`

2. **日期格式**
   - 必須使用 8 位數字格式：YYYYMMDD
   - 例如：2024年1月1日 → `20240101`

3. **股票代碼**
   - 不需要加上市場前綴
   - 多個股票用逗號分隔，不要有空格（或程式會自動去除空格）

4. **市場選擇**
   - TSE：只處理上市股票
   - OTC：只處理上櫃股票
   - BOTH：同時處理兩個市場（預設）

5. **輸出目錄**
   - 預設輸出到專案的 `data/decoded_quotes` 目錄
   - 可使用 `-o` 參數自訂輸出位置

## 常見問題

**Q: 找不到 Quote 檔案怎麼辦？**
A: 檢查檔案是否存在於 `C:\Users\tacor\Documents\tick-data`，檔名格式是否正確。

**Q: 可以一次處理多個日期嗎？**
A: 指定模式一次只能處理一個日期，如需處理多個日期請使用批次模式或多次執行。

**Q: 解碼後的資料放在哪裡？**
A: 預設在 `data/decoded_quotes/YYYYMMDD/` 目錄下，每支股票一個 parquet 檔案。

**Q: 如何查看解碼的結果？**
A: 可以使用 pandas 讀取 parquet 檔案：
```python
import pandas as pd
df = pd.read_parquet('data/decoded_quotes/20240101/2330.parquet')
print(df.head())
```
