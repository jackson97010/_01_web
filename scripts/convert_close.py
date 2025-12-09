#!/usr/bin/env python3
"""
將 close.parquet 轉換為 close.json
供 server.ts 使用
"""
import pandas as pd
import json
from pathlib import Path

from utils.config import DATA_DIR

def main():
    close_parquet = DATA_DIR / 'close.parquet'
    close_json = DATA_DIR / 'close.json'

    if not close_parquet.exists():
        print(f"錯誤: 找不到 {close_parquet}")
        return

    print(f"讀取 {close_parquet}")
    df = pd.read_parquet(close_parquet)

    # 轉換格式: { "YYYYMMDD": { "股票代碼": 收盤價, ... }, ... }
    result = {}

    for date_idx in df.index:
        date_str = date_idx.strftime('%Y%m%d')
        row_data = {}

        for stock_code in df.columns:
            price = df.loc[date_idx, stock_code]
            if pd.notna(price):
                row_data[stock_code] = round(float(price), 2)

        result[date_str] = row_data

    # 儲存 JSON
    print(f"儲存 {close_json}")
    with open(close_json, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

    print(f"完成！共 {len(result)} 個交易日")
    print(f"檔案大小: {close_json.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    main()
