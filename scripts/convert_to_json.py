"""
將解碼的 Parquet 檔案轉換為前端所需的 JSON 格式
修正版：支援 pandas Timestamp 對象和 Unix timestamp（毫秒）兩種格式
"""
import pandas as pd
import numpy as np
import os
import json
from pathlib import Path
from datetime import datetime
import glob


def determine_inner_outer(current_price, prev_bid1, prev_ask1):
    """
    判斷內外盤
    - 外盤：成交價 >= 前一檔賣1價
    - 內盤：成交價 <= 前一檔買1價
    - 其他：平盤
    """
    if pd.notna(prev_ask1) and current_price >= prev_ask1:
        return '外'
    elif pd.notna(prev_bid1) and current_price <= prev_bid1:
        return '內'
    else:
        return '–'


def timestamp_to_datetime_str(timestamp_value):
    """
    將 Timestamp 轉換為日期時間字串
    支援兩種輸入格式：
    1. pandas Timestamp 對象
    2. Unix timestamp in milliseconds (numeric)

    Args:
        timestamp_value: pandas.Timestamp 或 Unix timestamp (毫秒)

    Returns:
        str: 格式化的日期時間字串 'YYYY-MM-DD HH:MM:SS.ffffff'
    """
    try:
        # 檢查是否為 pandas Timestamp 對象
        if isinstance(timestamp_value, pd.Timestamp):
            # 直接格式化 Timestamp 對象
            return timestamp_value.strftime('%Y-%m-%d %H:%M:%S.%f')
        else:
            # 假設是 Unix timestamp（毫秒）
            timestamp_sec = float(timestamp_value) / 1000.0
            dt = datetime.fromtimestamp(timestamp_sec)
            return dt.strftime('%Y-%m-%d %H:%M:%S.%f')
    except Exception as e:
        print(f"    警告: 時間戳轉換失敗 {timestamp_value}: {e}")
        return "1970-01-01 00:00:00.000000"


def extract_date_from_timestamp(timestamp_value):
    """
    從 timestamp 提取日期字串（YYYYMMDD）
    支援兩種輸入格式：
    1. pandas Timestamp 對象
    2. Unix timestamp in milliseconds (numeric)
    """
    try:
        # 檢查是否為 pandas Timestamp 對象
        if isinstance(timestamp_value, pd.Timestamp):
            return timestamp_value.strftime('%Y%m%d')
        else:
            # 假設是 Unix timestamp（毫秒）
            timestamp_sec = float(timestamp_value) / 1000.0
            dt = datetime.fromtimestamp(timestamp_sec)
            return dt.strftime('%Y%m%d')
    except:
        return "19700101"


def process_stock_file(parquet_path, output_path):
    """
    處理單個股票的 Parquet 檔案，轉換為 JSON 格式
    """
    try:
        # 讀取 Parquet 檔案
        df = pd.read_parquet(parquet_path)

        if len(df) == 0:
            print(f"  警告: {os.path.basename(parquet_path)} 沒有資料")
            return False

        # 分離 Trade 和 Depth 資料
        trade_df = df[df['Type'] == 'Trade'].copy()
        depth_df = df[df['Type'] == 'Depth'].copy()

        # 提取股票代碼和日期
        stock_code = str(df['StockCode'].iloc[0]).strip()
        date_str = extract_date_from_timestamp(df['Datetime'].iloc[0])

        # === 1. 處理 trades（成交明細）===
        trades = []
        if len(trade_df) > 0:
            # 按時間排序（倒序，最新的在前）
            trade_df = trade_df.sort_values('Datetime', ascending=False).reset_index(drop=True)

            for idx, row in trade_df.iterrows():
                # 取得該交易時間點之前的最近一筆 Depth
                prev_depth = depth_df[depth_df['Datetime'] < row['Datetime']]

                prev_bid1 = None
                prev_ask1 = None

                if len(prev_depth) > 0:
                    latest_prev = prev_depth.iloc[-1]  # 取最後一筆（最接近的）
                    prev_bid1 = latest_prev.get('Bid1_Price')
                    prev_ask1 = latest_prev.get('Ask1_Price')

                    # 確保不是 NaN
                    if pd.isna(prev_bid1):
                        prev_bid1 = None
                    if pd.isna(prev_ask1):
                        prev_ask1 = None

                inner_outer = determine_inner_outer(row['Price'], prev_bid1, prev_ask1)

                trades.append({
                    'time': timestamp_to_datetime_str(row['Datetime']),
                    'price': float(row['Price']) if pd.notna(row['Price']) else 0.0,
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
                    'inner_outer': inner_outer,
                    'flag': int(row['Flag']) if pd.notna(row['Flag']) else 0
                })

        # === 2. 處理 depth_history（五檔歷史）===
        depth_history = []
        if len(depth_df) > 0:
            depth_df = depth_df.sort_values('Datetime').reset_index(drop=True)

            for _, row in depth_df.iterrows():
                bids = []
                asks = []

                # 提取買盤五檔
                for i in range(1, 6):
                    bid_price = row.get(f'Bid{i}_Price')
                    bid_volume = row.get(f'Bid{i}_Volume')
                    if pd.notna(bid_price) and pd.notna(bid_volume):
                        bids.append({
                            'price': float(bid_price),
                            'volume': int(bid_volume)
                        })

                # 提取賣盤五檔
                for i in range(1, 6):
                    ask_price = row.get(f'Ask{i}_Price')
                    ask_volume = row.get(f'Ask{i}_Volume')
                    if pd.notna(ask_price) and pd.notna(ask_volume):
                        asks.append({
                            'price': float(ask_price),
                            'volume': int(ask_volume)
                        })

                depth_history.append({
                    'timestamp': timestamp_to_datetime_str(row['Datetime']),
                    'bids': bids,
                    'asks': asks
                })

        # === 3. 處理 depth（當前五檔，取最新的）===
        depth = None
        if len(depth_history) > 0:
            latest_depth = depth_history[-1]
            depth = {
                'bids': latest_depth['bids'],
                'asks': latest_depth['asks'],
                'timestamp': latest_depth['timestamp']
            }

        # === 4. 處理 chart（圖表資料）===
        chart = None
        if len(trade_df) > 0:
            # 按時間正序排列用於圖表
            trade_df_asc = trade_df.sort_values('Datetime').reset_index(drop=True)

            timestamps = [timestamp_to_datetime_str(ts) for ts in trade_df_asc['Datetime']]
            prices = [float(p) if pd.notna(p) else 0.0 for p in trade_df_asc['Price']]
            volumes = [int(v) if pd.notna(v) else 0 for v in trade_df_asc['Volume']]

            # 計算累計成交量
            cumsum = 0
            total_volumes = []
            for v in volumes:
                cumsum += v
                total_volumes.append(cumsum)

            # 計算 VWAP（成交量加權平均價）
            vwap = []
            cumulative_amount = 0
            cumulative_volume = 0
            for price, volume in zip(prices, volumes):
                cumulative_amount += price * volume
                cumulative_volume += volume
                if cumulative_volume > 0:
                    vwap.append(cumulative_amount / cumulative_volume)
                else:
                    vwap.append(0.0)

            chart = {
                'timestamps': timestamps,
                'prices': prices,
                'volumes': volumes,
                'total_volumes': total_volumes,
                'vwap': vwap
            }

        # === 5. 處理 stats（統計資料）===
        stats = None
        if len(trade_df) > 0:
            trade_df_asc = trade_df.sort_values('Datetime').reset_index(drop=True)

            # 過濾掉 NaN 值
            valid_prices = trade_df_asc['Price'].dropna()
            valid_volumes = trade_df_asc['Volume'].dropna()

            if len(valid_prices) > 0:
                open_price = float(trade_df_asc['Price'].iloc[0])
                current_price = float(trade_df_asc['Price'].iloc[-1])
                high_price = float(valid_prices.max())
                low_price = float(valid_prices.min())

                # 計算平均成交價（成交量加權）
                valid_df = trade_df_asc[trade_df_asc['Price'].notna() & trade_df_asc['Volume'].notna()]
                if len(valid_df) > 0:
                    total_amount = (valid_df['Price'] * valid_df['Volume']).sum()
                    total_volume = valid_df['Volume'].sum()
                    avg_price = float(total_amount / total_volume) if total_volume > 0 else 0.0
                    trade_count = len(trade_df_asc)

                    change = current_price - open_price
                    change_pct = (change / open_price * 100) if open_price > 0 else 0.0

                    stats = {
                        'current_price': current_price,
                        'open_price': open_price,
                        'high_price': high_price,
                        'low_price': low_price,
                        'avg_price': avg_price,
                        'total_volume': int(total_volume),
                        'trade_count': trade_count,
                        'change': change,
                        'change_pct': change_pct
                    }

        # === 6. 組合最終資料 ===
        result = {
            'chart': chart,
            'depth': depth,
            'depth_history': depth_history,
            'trades': trades,
            'stats': stats,
            'stock_code': stock_code,
            'date': date_str
        }

        # 儲存為 JSON
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        print(f"  錯誤 {os.path.basename(parquet_path)}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主程式"""
    print("=" * 80)
    print("Parquet 轉 JSON 轉換程式（修正版）")
    print("=" * 80)

    # 設定路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    decoded_dir = os.path.join(project_root, 'data', 'decoded_quotes')
    output_dir = os.path.join(project_root, 'frontend', 'static', 'api')

    if not os.path.exists(decoded_dir):
        print(f"錯誤: 找不到解碼目錄 {decoded_dir}")
        print("請先執行 decode_quotes.py 或 batch_decode_quotes.py")
        return

    # 掃描所有日期目錄
    date_dirs = [d for d in os.listdir(decoded_dir)
                 if os.path.isdir(os.path.join(decoded_dir, d)) and d.isdigit()]

    date_dirs.sort()

    print(f"\n找到 {len(date_dirs)} 個日期: {date_dirs[0]} ~ {date_dirs[-1]}" if date_dirs else "沒有找到日期資料")

    if not date_dirs:
        return

    # 處理每個日期
    total_converted = 0
    total_failed = 0

    for date_str in date_dirs:
        print(f"\n處理日期: {date_str}")

        date_input_dir = os.path.join(decoded_dir, date_str)
        date_output_dir = os.path.join(output_dir, date_str)

        # 取得該日期的所有 parquet 檔案
        parquet_files = glob.glob(os.path.join(date_input_dir, "*.parquet"))

        if not parquet_files:
            print(f"  沒有找到 parquet 檔案")
            continue

        print(f"  找到 {len(parquet_files)} 個股票")

        converted = 0
        failed = 0

        for parquet_path in parquet_files:
            stock_code = os.path.splitext(os.path.basename(parquet_path))[0]
            output_path = os.path.join(date_output_dir, f"{stock_code}.json")

            # 檢查是否已存在
            if os.path.exists(output_path):
                # 比較修改時間
                parquet_mtime = os.path.getmtime(parquet_path)
                json_mtime = os.path.getmtime(output_path)

                if json_mtime > parquet_mtime:
                    # JSON 較新，跳過
                    continue

            # 轉換
            if process_stock_file(parquet_path, output_path):
                converted += 1
                if converted % 10 == 0:
                    print(f"  已轉換: {converted}/{len(parquet_files)}")
            else:
                failed += 1

        print(f"  完成: 成功={converted}, 失敗={failed}, 跳過={len(parquet_files)-converted-failed}")
        total_converted += converted
        total_failed += failed

    print("\n" + "=" * 80)
    print("轉換完成！")
    print(f"總共轉換: {total_converted} 個檔案")
    if total_failed > 0:
        print(f"失敗: {total_failed} 個檔案")
    print(f"輸出目錄: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
