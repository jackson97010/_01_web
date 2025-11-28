#!/usr/bin/env python3
"""
測試同時解碼 OTC 和 TSE 檔案
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


def test_both_files():
    """測試 OTC 和 TSE 兩個檔案"""
    print("=" * 80)
    print("測試 OTC 和 TSE Quote 解碼")
    print("=" * 80)

    # 設定路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    base_dir = os.path.join(project_root, 'data')
    limit_up_file = os.path.join(base_dir, 'lup_ma20_filtered.parquet')
    otc_file = os.path.join(base_dir, 'OTCQuote.20251031')
    tse_file = os.path.join(base_dir, 'TSEQuote.20251031')
    output_base_dir = os.path.join(base_dir, 'decoded_quotes_test')

    # 檢查檔案
    if not os.path.exists(limit_up_file):
        print(f"錯誤：找不到漲停清單檔案 {limit_up_file}")
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
        print(f"  清單: {stocks_30}")
    else:
        print("  (無資料)")

    print(f"\n{date_20251031} 的漲停股票:")
    if date_20251031 in limit_up_dict:
        stocks_31 = sorted(list(limit_up_dict[date_20251031]))
        print(f"  數量: {len(stocks_31)}")
        print(f"  清單: {stocks_31}")
    else:
        print("  (無資料)")

    # 獲取需要處理的股票
    target_stocks = get_target_stocks(limit_up_dict, date_20251031)
    print(f"\n需要處理的總股票數: {len(target_stocks)}")
    print(f"股票清單: {sorted(list(target_stocks))}")

    # 處理 OTC 檔案
    if os.path.exists(otc_file):
        print(f"\n處理 OTC 檔案...")
        process_quote_file(otc_file, limit_up_dict, output_base_dir)
    else:
        print(f"警告：找不到 {otc_file}")

    # 處理 TSE 檔案
    if os.path.exists(tse_file):
        print(f"\n處理 TSE 檔案...")
        process_quote_file(tse_file, limit_up_dict, output_base_dir)
    else:
        print(f"警告：找不到 {tse_file}")

    # 檢查結果
    print("\n" + "=" * 80)
    print("檢查解碼結果")
    print("=" * 80)

    output_dir = os.path.join(output_base_dir, date_20251031)
    if os.path.exists(output_dir):
        files = sorted([f for f in os.listdir(output_dir) if f.endswith('.parquet')])
        print(f"\n共產生 {len(files)} 個 parquet 檔案")
        print(f"檔案清單: {files}")

        # 驗證是否所有目標股票都已處理
        processed_stocks = set([f.replace('.parquet', '') for f in files])
        missing_stocks = target_stocks - processed_stocks
        if missing_stocks:
            print(f"\n警告：以下股票未處理: {sorted(list(missing_stocks))}")
        else:
            print(f"\n所有 {len(target_stocks)} 支股票都已成功處理！")

        # 檢查幾個範例
        print("\n檢查範例資料:")
        for fname in files[:3]:
            fpath = os.path.join(output_dir, fname)
            df = pd.read_parquet(fpath)
            stock_id = fname.replace('.parquet', '')
            print(f"\n{stock_id}:")
            print(f"  記錄數: {len(df)}")

            # 檢查價格
            if 'Price' in df.columns:
                prices = df['Price'].dropna()
                if len(prices) > 0:
                    print(f"  成交價格範圍: {prices.min():.2f} ~ {prices.max():.2f}")
                    print(f"  範例成交記錄:")
                    trades = df[df['Type'] == 'Trade'][['Datetime', 'Price', 'Volume']].head(3)
                    print(trades.to_string(index=False))

    else:
        print(f"錯誤：找不到輸出目錄 {output_dir}")

    print("\n" + "=" * 80)
    print("測試完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_both_files()
