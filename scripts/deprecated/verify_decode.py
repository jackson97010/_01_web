"""
驗證解碼結果的腳本
檢查解碼的資料是否正確
"""
import pandas as pd
import os
from pathlib import Path


def verify_decoded_file(file_path):
    """驗證單個解碼檔案"""
    print(f"\n{'='*60}")
    print(f"檢查檔案: {file_path}")
    print(f"{'='*60}")

    try:
        df = pd.read_parquet(file_path)

        # 基本資訊
        print(f"\n1. 基本資訊:")
        print(f"   總記錄數: {len(df)}")

        # 資料類型統計
        type_counts = df['Type'].value_counts()
        print(f"\n2. 資料類型分布:")
        for dtype, count in type_counts.items():
            print(f"   {dtype}: {count} 筆")

        # Trade 資料檢查
        if 'Trade' in type_counts:
            trade_df = df[df['Type'] == 'Trade']
            print(f"\n3. Trade 資料檢查:")
            print(f"   價格範圍: {trade_df['Price'].min():.2f} ~ {trade_df['Price'].max():.2f}")
            print(f"   平均價格: {trade_df['Price'].mean():.2f}")
            print(f"   成交量範圍: {trade_df['Volume'].min():.0f} ~ {trade_df['Volume'].max():.0f}")

            # 檢查試撮旗標
            flag_counts = trade_df['Flag'].value_counts()
            print(f"   試撮旗標分布:")
            for flag, count in flag_counts.items():
                flag_name = "試算揭示" if flag == 1 else "一般揭示"
                print(f"      {int(flag)} ({flag_name}): {count} 筆")

            # 顯示範例
            print(f"\n   Trade 範例 (前3筆):")
            for idx, row in trade_df.head(3).iterrows():
                print(f"      時間: {row['Datetime']}")
                print(f"        價格: {row['Price']:.2f}, 量: {int(row['Volume'])}, 試撮: {int(row['Flag'])}")

        # Depth 資料檢查
        if 'Depth' in type_counts:
            depth_df = df[df['Type'] == 'Depth']
            print(f"\n4. Depth 資料檢查:")

            # 檢查買賣盤檔數
            avg_bid_count = depth_df['BidCount'].mean()
            avg_ask_count = depth_df['AskCount'].mean()
            print(f"   平均買盤檔數: {avg_bid_count:.1f}")
            print(f"   平均賣盤檔數: {avg_ask_count:.1f}")

            # 檢查買1價格範圍
            bid1_prices = depth_df['Bid1_Price'].dropna()
            if len(bid1_prices) > 0:
                print(f"   買1價格範圍: {bid1_prices.min():.2f} ~ {bid1_prices.max():.2f}")

            # 檢查賣1價格範圍
            ask1_prices = depth_df['Ask1_Price'].dropna()
            if len(ask1_prices) > 0:
                print(f"   賣1價格範圍: {ask1_prices.min():.2f} ~ {ask1_prices.max():.2f}")

            # 顯示範例
            print(f"\n   Depth 範例 (前2筆):")
            for idx, row in depth_df.head(2).iterrows():
                print(f"      時間: {row['Datetime']}")
                print(f"        買盤: {int(row['BidCount'])}檔")

                # 顯示前3檔買盤
                for i in range(1, 4):
                    bid_price = row[f'Bid{i}_Price']
                    bid_vol = row[f'Bid{i}_Volume']
                    if pd.notna(bid_price):
                        print(f"          買{i}: {bid_price:.2f} * {int(bid_vol)}")

                print(f"        賣盤: {int(row['AskCount'])}檔")

                # 顯示前3檔賣盤
                for i in range(1, 4):
                    ask_price = row[f'Ask{i}_Price']
                    ask_vol = row[f'Ask{i}_Volume']
                    if pd.notna(ask_price):
                        print(f"          賣{i}: {ask_price:.2f} * {int(ask_vol)}")
                    else:
                        break

        # 時間範圍
        print(f"\n5. 時間範圍:")
        print(f"   開始: {df['Datetime'].min()}")
        print(f"   結束: {df['Datetime'].max()}")

        # 資料完整性檢查
        print(f"\n6. 資料完整性:")
        null_counts = df.isnull().sum()
        critical_fields = ['Type', 'StockCode', 'Datetime', 'Timestamp']
        has_null = False
        for field in critical_fields:
            if null_counts[field] > 0:
                print(f"   [WARNING] {field} 有 {null_counts[field]} 個空值")
                has_null = True

        if not has_null:
            print(f"   [OK] 關鍵欄位無空值")

        print(f"\n[OK] 檔案檢查完成")
        return True

    except Exception as e:
        print(f"\n[ERROR] 錯誤: {e}")
        return False


def main():
    """主程式"""
    print("=" * 80)
    print("解碼結果驗證程式")
    print("=" * 80)

    # 設定路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    decoded_dir = os.path.join(project_root, 'data', 'decoded_quotes')

    if not os.path.exists(decoded_dir):
        print(f"\n錯誤: 找不到解碼目錄 {decoded_dir}")
        print("請先執行 decode_quotes.py 或 batch_decode_quotes.py")
        return

    # 掃描解碼目錄
    date_dirs = [d for d in os.listdir(decoded_dir)
                 if os.path.isdir(os.path.join(decoded_dir, d))]

    if not date_dirs:
        print(f"\n錯誤: 解碼目錄中沒有日期資料夾")
        return

    date_dirs.sort()
    print(f"\n找到 {len(date_dirs)} 個日期: {date_dirs[0]} ~ {date_dirs[-1]}")

    # 選擇最新日期進行驗證
    latest_date = date_dirs[-1]
    date_dir = os.path.join(decoded_dir, latest_date)

    print(f"\n驗證日期: {latest_date}")

    # 掃描該日期的股票檔案
    stock_files = [f for f in os.listdir(date_dir) if f.endswith('.parquet')]

    if not stock_files:
        print(f"\n錯誤: 日期 {latest_date} 沒有股票檔案")
        return

    print(f"該日期有 {len(stock_files)} 支股票")

    # 驗證前3支股票（或全部，如果少於3支）
    num_to_verify = min(3, len(stock_files))
    print(f"\n將驗證其中 {num_to_verify} 支股票的資料...")

    success_count = 0
    for i, stock_file in enumerate(sorted(stock_files)[:num_to_verify]):
        file_path = os.path.join(date_dir, stock_file)
        if verify_decoded_file(file_path):
            success_count += 1

    print("\n" + "=" * 80)
    print(f"驗證完成: {success_count}/{num_to_verify} 支股票通過檢查")

    if success_count == num_to_verify:
        print("[OK] 所有檢查的股票資料格式正確")
    else:
        print("[WARNING] 部分股票資料可能有問題，請檢查")

    print("=" * 80)


if __name__ == "__main__":
    main()
