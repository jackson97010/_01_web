# 舊版程式碼（已廢棄）

此資料夾包含已被優化版本取代的舊版腳本。

## ⚠️ 請勿使用

這些檔案保留僅供參考。請使用上層目錄中的新版腳本：

| 舊版（此資料夾）| 新版（推薦使用）|
|----------------|----------------|
| `batch_decode_quotes.py` | `../batch_decode.py` |
| `decode_quotes_correct.py` | `../batch_decode.py` |
| `batch_process.py` | `../batch_decode.py` |
| `convert_to_json.py` (如有) | `../data_convert.py` |
| `get_single_stock_data.py` (如有) | `../query_stock.py` |

## 為什麼廢棄？

- ❌ 程式碼重複率高
- ❌ 缺乏模組化設計
- ❌ 沒有統一的日誌系統
- ❌ 維護困難

## 新版優勢

- ✅ 模組化設計（`utils/` 工具模組）
- ✅ 消除程式碼重複
- ✅ 統一的日誌和錯誤處理
- ✅ 更好的效能和可維護性

詳見 [CODE_REFACTORING_GUIDE.md](../../CODE_REFACTORING_GUIDE.md)
