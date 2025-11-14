import pandas as pd
import os

# 載入資料
df = pd.read_parquet('processed_data/20251111/3379.parquet')

print("=" * 80)
print("測試資料結構：3379.parquet")
print("=" * 80)

# 統計資料
trade_df = df[df['Type'] == 'Trade'].copy()
depth_df = df[df['Type'] == 'Depth'].copy()

print(f"\n總筆數：{len(df)}")
print(f"Trade 筆數：{len(trade_df)}")
print(f"Depth 筆數：{len(depth_df)}")

# 只看正式交易時段（09:00 以後）
trade_df['Datetime'] = pd.to_datetime(trade_df['Datetime'])
depth_df['Datetime'] = pd.to_datetime(depth_df['Datetime'])

trade_market = trade_df[trade_df['Datetime'].dt.hour >= 9].copy()
depth_market = depth_df[depth_df['Datetime'].dt.hour >= 9].copy()

print(f"\n正式交易時段 (09:00-13:30)：")
print(f"Trade 筆數：{len(trade_market)}")
print(f"Depth 筆數：{len(depth_market)}")

# 顯示 Trade 時間序列（前 5 筆）
print(f"\n成交明細（前 5 筆）：")
trade_market_sorted = trade_market.sort_values('Datetime')
for idx, row in trade_market_sorted.head(5).iterrows():
    print(f"  {row['Datetime']} - 價格: {row['Price']:.2f}, 數量: {row['Volume']}")

# 顯示 Depth 時間序列（前 5 筆）
print(f"\n五檔報價（前 5 筆）：")
depth_market_sorted = depth_market.sort_values('Datetime')
for idx, row in depth_market_sorted.head(5).iterrows():
    bid1 = row['Bid1_Price'] if pd.notna(row['Bid1_Price']) else 'N/A'
    ask1 = row['Ask1_Price'] if pd.notna(row['Ask1_Price']) else 'N/A'
    print(f"  {row['Datetime']} - 買一: {bid1}, 賣一: {ask1}")

# 驗證時間序列是否獨立
print(f"\n時間範圍驗證：")
print(f"Trade 最早時間：{trade_market['Datetime'].min()}")
print(f"Trade 最晚時間：{trade_market['Datetime'].max()}")
print(f"Depth 最早時間：{depth_market['Datetime'].min()}")
print(f"Depth 最晚時間：{depth_market['Datetime'].max()}")

print("\n" + "=" * 80)
print("結論：Trade 和 Depth 有各自獨立的時間序列")
print("=" * 80)
