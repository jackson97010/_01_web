#!/usr/bin/env python3
"""
測試單個檔案的解碼結果
用於驗證 OTCQuote.20251031 的解碼是否正確
"""

import pandas as pd
import sys
import os

# 加入 scripts 目錄到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decode_quotes_correct import (
    load_limit_up_list,
    get_target_stocks,
    process_quote_file
)


def test_single_file():
    """測試單個檔案"""
    print("=" * 80)
    print("測試 OTCQuote.20251031 解碼")
    print("=" * 80)

    # 設定路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    base_dir = os.path.join(project_root, 'data')
    limit_up_file = os.path.join(base_dir, 'lup_ma20_filtered.parquet')
    quote_file = os.path.join(base_dir, 'OTCQuote.20251031')
    output_base_dir = os.path.join(base_dir, 'decoded_quotes_test')

    # 檢查檔案
    if not os.path.exists(limit_up_file):
        print(f"錯誤：找不到漲停清單檔案 {limit_up_file}")
        return

    if not os.path.exists(quote_file):
        print(f"錯誤：找不到 Quote 檔案 {quote_file}")
        return

    # 載入漲停清單
    print(f"\n載入漲停清單...")
    limit_up_dict = load_limit_up_list(limit_up_file)

    # 查看 2025-10-30 和 2025-10-31 的股票清單
    date_20251030 = '20251030'
    date_20251031 = '20251031'

    print(f"\n{date_20251030} 的漲停股票:")
    if date_20251030 in limit_up_dict:
        stocks_30 = sorted(list(limit_up_dict[date_20251030]))
        print(f"  數量: {len(stocks_30)}")
        print(f"  清單: {stocks_30[:20]}" + ("..." if len(stocks_30) > 20 else ""))
    else:
        print("  (無資料)")

    print(f"\n{date_20251031} 的漲停股票:")
    if date_20251031 in limit_up_dict:
        stocks_31 = sorted(list(limit_up_dict[date_20251031]))
        print(f"  數量: {len(stocks_31)}")
        print(f"  清單: {stocks_31[:20]}" + ("..." if len(stocks_31) > 20 else ""))
    else:
        print("  (無資料)")

    # 獲取需要處理的股票
    target_stocks = get_target_stocks(limit_up_dict, date_20251031)
    print(f"\n需要處理的總股票數: {len(target_stocks)}")

    # 處理檔案
    print(f"\n開始處理 {quote_file}...")
    process_quote_file(quote_file, limit_up_dict, output_base_dir)

    # 檢查結果
    print("\n" + "=" * 80)
    print("檢查解碼結果")
    print("=" * 80)

    output_dir = os.path.join(output_base_dir, date_20251031)
    if os.path.exists(output_dir):
        files = [f for f in os.listdir(output_dir) if f.endswith('.parquet')]
        print(f"\n共產生 {len(files)} 個 parquet 檔案")

        # 隨機抽取幾個檔案檢查
        if files:
            print("\n檢查前3個檔案的內容:")
            for fname in sorted(files)[:3]:
                fpath = os.path.join(output_dir, fname)
                df = pd.read_parquet(fpath)
                print(f"\n{fname}:")
                print(f"  記錄數: {len(df)}")
                print(f"  欄位: {df.columns.tolist()}")
                print(f"\n  前5筆資料:")
                print(df.head())

                # 檢查價格是否合理
                if 'Price' in df.columns:
                    prices = df['Price'].dropna()
                    if len(prices) > 0:
                        print(f"\n  價格統計:")
                        print(f"    最小值: {prices.min():.4f}")
                        print(f"    最大值: {prices.max():.4f}")
                        print(f"    平均值: {prices.mean():.4f}")

    else:
        print(f"錯誤：找不到輸出目錄 {output_dir}")

    print("\n" + "=" * 80)
    print("測試完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_single_file()
