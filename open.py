import pandas as pd
import os
import re
from datetime import datetime

# 檔案路徑
file_path = 'TSEQuote.20251031'

# 從檔案名稱中提取日期並創建輸出目錄
date_str = re.search(r'(\d{8})', os.path.basename(file_path)).group(1)
output_dir = date_str
os.makedirs(output_dir, exist_ok=True)

# 初始化兩個列表，分別用來存放兩種格式的資料
trade_data = []
depth_data = []

# 定義欄位名稱
trade_columns = ['Type', 'StockCode', 'Timestamp', 'Flag', 'Price', 'Volume', 'TotalVolume']

# 更新 Depth 的欄位名稱，將買賣報價保留為原始欄位（後續拆分）
depth_columns = [
    'Type', 'StockCode', 'Timestamp', 'BidCount',
    'Bid1_Raw', 'Bid2_Raw', 'Bid3_Raw', 'Bid4_Raw', 'Bid5_Raw',
    'AskCount', 'Ask1_Raw', 'Ask2_Raw', 'Ask3_Raw', 'Ask4_Raw', 'Ask5_Raw'
]

def split_price_volume(value):
    """拆分價格*數量的字串，返回價格和數量"""
    if pd.isna(value) or '*' not in str(value):
        return pd.NA, pd.NA
    try:
        price_str, volume_str = str(value).split('*')
        price = float(price_str) / 10000  # 價格需要除以 10000
        volume = int(volume_str)
        return price, volume
    except (ValueError, TypeError):
        return pd.NA, pd.NA

# 使用 try-except 確保檔案存在
try:
    # 逐行讀取檔案
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 去除頭尾的空白並用逗號分割
            fields = line.strip().split(',')

            if not fields:
                continue

            # 根據第一個欄位判斷資料類型
            if fields[0] == 'Trade' and len(fields) == 7:
                trade_data.append(fields)
            elif fields[0] == 'Depth':
                # Depth 格式的欄位數較多，這裡直接加入
                depth_data.append(fields)

    # 用於存儲所有股票代碼的集合
    stock_codes = set()

    # --- 建立 Trade DataFrame ---
    if trade_data:
        df_trade = pd.DataFrame(trade_data, columns=trade_columns)

        # 資料型態轉換與處理
        df_trade['StockCode'] = df_trade['StockCode'].str.strip()
        # 轉為數字（保留 NaN），並建立 datetime 欄位（假設格式為 hhmmss + 6 microseconds -> 12 digits）
        df_trade['Timestamp'] = pd.to_numeric(df_trade['Timestamp'], errors='coerce').astype('Int64')
        s = df_trade['Timestamp'].astype('Int64').astype(str).str.zfill(12)
        df_trade['Datetime'] = pd.to_datetime(date_str + s, format='%Y%m%d%H%M%S%f', errors='coerce')

        # 價格與其他數值欄位
        df_trade['Price'] = pd.to_numeric(df_trade['Price'], errors='coerce') / 10000
        numeric_cols = ['Flag', 'Volume', 'TotalVolume']
        for col in numeric_cols:
            df_trade[col] = pd.to_numeric(df_trade[col], errors='coerce')

        # 收集股票代碼
        stock_codes.update(df_trade['StockCode'].dropna().unique())

        print("--- 成交資料 (Trade) ---")
        print(df_trade.head())
        print(f"Trade 資料筆數: {len(df_trade)}")
        print("\n")

    # --- 建立 Depth DataFrame ---
    if depth_data:
        try:
            # 先建立基本的 DataFrame
            df_depth = pd.DataFrame(depth_data, columns=depth_columns)
            df_depth['StockCode'] = df_depth['StockCode'].str.strip()

            # 轉 Timestamp 並建立 Datetime
            df_depth['Timestamp'] = pd.to_numeric(df_depth['Timestamp'], errors='coerce').astype('Int64')
            s = df_depth['Timestamp'].astype('Int64').astype(str).str.zfill(12)
            df_depth['Datetime'] = pd.to_datetime(date_str + s, format='%Y%m%d%H%M%S%f', errors='coerce')

            # 處理買賣報價的檔位，拆分價格和數量
            for i in range(1, 6):
                bid_prices = []
                bid_volumes = []
                for value in df_depth[f'Bid{i}_Raw']:
                    price, volume = split_price_volume(value)
                    bid_prices.append(price)
                    bid_volumes.append(volume)
                df_depth[f'Bid{i}_Price'] = bid_prices
                df_depth[f'Bid{i}_Volume'] = bid_volumes

                ask_prices = []
                ask_volumes = []
                for value in df_depth[f'Ask{i}_Raw']:
                    price, volume = split_price_volume(value)
                    ask_prices.append(price)
                    ask_volumes.append(volume)
                df_depth[f'Ask{i}_Price'] = ask_prices
                df_depth[f'Ask{i}_Volume'] = ask_volumes

            # 刪除原始的未拆分欄位
            raw_columns = [col for col in df_depth.columns if '_Raw' in col]
            df_depth = df_depth.drop(columns=raw_columns)

            # 正確處理 BidCount 和 AskCount
            df_depth['BidCount'] = df_depth['BidCount'].str.extract(r'BID:(\d+)').astype(float)
            df_depth['AskCount'] = df_depth['AskCount'].str.extract(r'ASK:(\d+)').astype(float)

            # 收集股票代碼
            stock_codes.update(df_depth['StockCode'].dropna().unique())

            print("--- 五檔報價資料 (Depth) ---")
            print(df_depth.head())
            print(f"Depth 資料筆數: {len(df_depth)}")
            print("\n欄位名稱：")
            print(df_depth.columns.tolist())

        except ValueError as ve:
            print(f"建立 Depth DataFrame 失敗: {ve}")
            print("可能是因為 'Depth' 資料列的欄位數量不一致。")
            raise

    # --- 依照股票代碼分別處理並儲存 ---
    print(f"\n開始處理並儲存各股票資料...")
    for stock_code in sorted(stock_codes):
        # 篩選該股票的資料並建立副本以避免 SettingWithCopyWarning
        stock_trades = df_trade[df_trade['StockCode'] == stock_code].copy() if 'df_trade' in locals() else pd.DataFrame()
        stock_depths = df_depth[df_depth['StockCode'] == stock_code].copy() if 'df_depth' in locals() else pd.DataFrame()

        # 合併該股票的所有資料
        if not stock_trades.empty and not stock_depths.empty:
            all_columns = sorted(list(set(stock_trades.columns) | set(stock_depths.columns)))

            # 為缺失欄位建立適當的空值
            for col in all_columns:
                if col not in stock_trades.columns:
                    stock_trades.loc[:, col] = pd.NA
                if col not in stock_depths.columns:
                    stock_depths.loc[:, col] = pd.NA

            # 使用相同的欄位順序
            stock_trades = stock_trades.reindex(columns=all_columns)
            stock_depths = stock_depths.reindex(columns=all_columns)

            # 合併資料
            stock_data = pd.concat([stock_trades, stock_depths], ignore_index=True)
        elif not stock_trades.empty:
            stock_data = stock_trades
        elif not stock_depths.empty:
            stock_data = stock_depths
        else:
            continue

        # 儲存檔案（保留 Datetime 欄位）
        output_path = os.path.join(output_dir, f"{stock_code}.parquet")
        stock_data.to_parquet(output_path)
        print(f"已儲存 {stock_code}.parquet (共 {len(stock_data)} 筆記錄)")

except FileNotFoundError:
    print(f"錯誤：找不到檔案 {file_path}")
except Exception as e:
    print(f"處理檔案時發生錯誤: {e}")
    raise