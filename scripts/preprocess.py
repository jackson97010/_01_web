"""
預處理腳本：將所有 Parquet 檔案轉換成靜態 JSON 檔案
用於 Nginx 直接服務，達到極致效能
"""
import pandas as pd
import os
import json
import glob
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import time

# 從 web_viewer.py 複製必要的函數
def prepare_chart_data(df):
    """準備圖表資料"""
    if df is None or df.empty:
        return None

    trade_df = df[df['Type'] == 'Trade'].copy()
    if trade_df.empty:
        return None

    if 'Datetime' not in trade_df.columns:
        return None

    trade_df = trade_df.sort_values('Datetime')

    if not pd.api.types.is_datetime64_any_dtype(trade_df['Datetime']):
        trade_df['Datetime'] = pd.to_datetime(trade_df['Datetime'])

    def filter_premarket_volume(row):
        time = row['Datetime']
        if time.hour == 8 and 45 <= time.minute <= 59:
            return 0
        return row['Volume']

    trade_df['FilteredVolume'] = trade_df.apply(filter_premarket_volume, axis=1)
    trade_df_market = trade_df[trade_df['Datetime'].dt.hour >= 9].copy()

    if trade_df_market.empty:
        return None

    # 向量化計算 VWAP（優化版）
    prices = trade_df_market['Price'].fillna(0).values
    volumes = trade_df_market['FilteredVolume'].fillna(0).values

    cumulative_pv = (prices * volumes).cumsum()
    cumulative_volume = volumes.cumsum()

    # 避免除以零
    vwap_values = []
    for i in range(len(cumulative_volume)):
        if cumulative_volume[i] > 0:
            vwap_values.append(cumulative_pv[i] / cumulative_volume[i])
        else:
            vwap_values.append(prices[i])

    chart_data = {
        'timestamps': trade_df_market['Datetime'].astype(str).tolist(),
        'prices': trade_df_market['Price'].fillna(0).tolist(),
        'volumes': trade_df_market['FilteredVolume'].fillna(0).tolist(),
        'total_volumes': trade_df_market['TotalVolume'].fillna(0).tolist(),
        'vwap': vwap_values
    }

    return chart_data

def prepare_depth_data(df):
    """準備五檔資料（取最新一筆）"""
    if df is None or df.empty:
        return None

    depth_df = df[df['Type'] == 'Depth'].copy()
    if depth_df.empty:
        return None

    depth_df = depth_df.sort_values('Datetime', ascending=False)
    latest = depth_df.iloc[0]

    bids = []
    asks = []

    for i in range(1, 6):
        bid_price_col = f'Bid{i}_Price'
        bid_volume_col = f'Bid{i}_Volume'
        ask_price_col = f'Ask{i}_Price'
        ask_volume_col = f'Ask{i}_Volume'

        if bid_price_col in latest and bid_volume_col in latest:
            bid_price = latest[bid_price_col]
            bid_volume = latest[bid_volume_col]
            if pd.notna(bid_price) and pd.notna(bid_volume):
                bids.append({
                    'price': float(bid_price),
                    'volume': int(bid_volume)
                })

        if ask_price_col in latest and ask_volume_col in latest:
            ask_price = latest[ask_price_col]
            ask_volume = latest[ask_volume_col]
            if pd.notna(ask_price) and pd.notna(ask_volume):
                asks.append({
                    'price': float(ask_price),
                    'volume': int(ask_volume)
                })

    return {
        'bids': bids,
        'asks': asks,
        'timestamp': str(latest['Datetime']) if 'Datetime' in latest else ''
    }

def prepare_depth_history(df):
    """準備五檔歷史資料"""
    if df is None or df.empty:
        return []

    depth_df = df[df['Type'] == 'Depth'].copy()
    if depth_df.empty:
        return []

    if 'Datetime' not in depth_df.columns:
        return []

    if not pd.api.types.is_datetime64_any_dtype(depth_df['Datetime']):
        depth_df['Datetime'] = pd.to_datetime(depth_df['Datetime'])

    depth_df = depth_df[depth_df['Datetime'].dt.hour >= 9].copy()
    depth_df = depth_df.sort_values('Datetime')

    history = []
    for _, row in depth_df.iterrows():
        entry = {
            'timestamp': str(row['Datetime']),
            'bids': [],
            'asks': []
        }

        for i in range(1, 6):
            bid_price_col = f'Bid{i}_Price'
            bid_volume_col = f'Bid{i}_Volume'
            ask_price_col = f'Ask{i}_Price'
            ask_volume_col = f'Ask{i}_Volume'

            if bid_price_col in row and bid_volume_col in row:
                if pd.notna(row[bid_price_col]) and pd.notna(row[bid_volume_col]):
                    entry['bids'].append({
                        'price': float(row[bid_price_col]),
                        'volume': int(row[bid_volume_col])
                    })

            if ask_price_col in row and ask_volume_col in row:
                if pd.notna(row[ask_price_col]) and pd.notna(row[ask_volume_col]):
                    entry['asks'].append({
                        'price': float(row[ask_price_col]),
                        'volume': int(row[ask_volume_col])
                    })

        history.append(entry)

    return history

def prepare_trade_details(df):
    """準備成交明細"""
    if df is None or df.empty:
        return []

    trade_df = df[df['Type'] == 'Trade'].copy()
    if trade_df.empty:
        return []

    if 'Datetime' not in trade_df.columns:
        return []

    if not pd.api.types.is_datetime64_any_dtype(trade_df['Datetime']):
        trade_df['Datetime'] = pd.to_datetime(trade_df['Datetime'])

    trade_df = trade_df[trade_df['Datetime'].dt.hour >= 9].copy()

    depth_df = df[df['Type'] == 'Depth'].copy()
    if not depth_df.empty and 'Datetime' in depth_df.columns:
        if not pd.api.types.is_datetime64_any_dtype(depth_df['Datetime']):
            depth_df['Datetime'] = pd.to_datetime(depth_df['Datetime'])
        depth_df = depth_df[depth_df['Datetime'].dt.hour >= 9].copy()
        depth_df = depth_df.sort_values('Datetime')
    else:
        depth_df = pd.DataFrame()

    trade_df = trade_df.sort_values('Datetime', ascending=False)

    details = []
    for _, row in trade_df.iterrows():
        trade_time = row['Datetime']
        trade_price = float(row['Price']) if pd.notna(row['Price']) else 0

        inner_outer = '–'
        if not depth_df.empty and trade_price > 0:
            prior_depths = depth_df[depth_df['Datetime'] <= trade_time]
            if not prior_depths.empty:
                closest_depth = prior_depths.iloc[-1]

                bid1_price = closest_depth.get('Bid1_Price')
                ask1_price = closest_depth.get('Ask1_Price')

                if pd.notna(bid1_price) and trade_price <= bid1_price:
                    inner_outer = '內盤'
                elif pd.notna(ask1_price) and trade_price >= ask1_price:
                    inner_outer = '外盤'
                else:
                    if pd.notna(bid1_price) and pd.notna(ask1_price):
                        mid_price = (bid1_price + ask1_price) / 2
                        if trade_price <= mid_price:
                            inner_outer = '內盤'
                        else:
                            inner_outer = '外盤'

        details.append({
            'time': str(trade_time) if pd.notna(trade_time) else '',
            'price': trade_price,
            'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
            'inner_outer': inner_outer,
            'flag': int(row['Flag']) if pd.notna(row['Flag']) else 0
        })

    return details

def calculate_statistics(df):
    """計算統計資料"""
    if df is None or df.empty:
        return None

    trade_df = df[df['Type'] == 'Trade'].copy()
    if trade_df.empty:
        return None

    if 'Datetime' not in trade_df.columns:
        return None

    if not pd.api.types.is_datetime64_any_dtype(trade_df['Datetime']):
        trade_df['Datetime'] = pd.to_datetime(trade_df['Datetime'])

    trade_df_market = trade_df[trade_df['Datetime'].dt.hour >= 9].copy()
    if trade_df_market.empty:
        return None

    prices = trade_df_market['Price'].dropna()
    volumes = trade_df_market['Volume'].dropna()

    if prices.empty:
        return None

    valid_trades = trade_df_market[trade_df_market['Price'].notna() & trade_df_market['Volume'].notna()].copy()
    if not valid_trades.empty:
        total_pv = (valid_trades['Price'] * valid_trades['Volume']).sum()
        total_volume = valid_trades['Volume'].sum()
        avg_price = total_pv / total_volume if total_volume > 0 else 0
    else:
        avg_price = 0

    stats = {
        'current_price': float(prices.iloc[-1]) if len(prices) > 0 else 0,
        'open_price': float(prices.iloc[0]) if len(prices) > 0 else 0,
        'high_price': float(prices.max()),
        'low_price': float(prices.min()),
        'avg_price': float(avg_price),
        'total_volume': int(trade_df_market['TotalVolume'].max()) if 'TotalVolume' in trade_df_market else 0,
        'trade_count': len(trade_df_market)
    }

    if stats['open_price'] > 0:
        change = stats['current_price'] - stats['open_price']
        change_pct = (change / stats['open_price']) * 100
        stats['change'] = float(change)
        stats['change_pct'] = float(change_pct)
    else:
        stats['change'] = 0
        stats['change_pct'] = 0

    return stats

def process_single_parquet(args):
    """處理單一 Parquet 檔案並轉成 JSON"""
    parquet_file, output_base_dir = args

    try:
        # 解析路徑：data/processed_data/20251112/2330.parquet
        path_parts = Path(parquet_file).parts
        date_str = path_parts[-2]  # 20251112
        stock_code = Path(parquet_file).stem  # 2330

        # 檢查輸出檔案是否已存在
        output_dir = os.path.join(output_base_dir, date_str)
        output_file = os.path.join(output_dir, f"{stock_code}.json")

        if os.path.exists(output_file):
            return f"跳過 {date_str}/{stock_code} (已存在)"

        # 讀取 Parquet
        df = pd.read_parquet(parquet_file)

        # 準備所有資料
        chart_data = prepare_chart_data(df)
        depth_data = prepare_depth_data(df)
        depth_history = prepare_depth_history(df)
        trade_details = prepare_trade_details(df)
        statistics = calculate_statistics(df)

        # 組合成 API 格式
        api_response = {
            'chart': chart_data,
            'depth': depth_data,
            'depth_history': depth_history,
            'trades': trade_details,
            'stats': statistics,
            'stock_code': stock_code,
            'date': date_str
        }

        # 建立輸出目錄
        os.makedirs(output_dir, exist_ok=True)

        # 寫入 JSON（壓縮格式）
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(api_response, f, ensure_ascii=False, separators=(',', ':'))

        return f"完成 {date_str}/{stock_code}"

    except Exception as e:
        return f"錯誤 {parquet_file}: {e}"

def main():
    """主程式"""
    print("=" * 80)
    print("Parquet → JSON 預處理程式")
    print("將所有 Parquet 轉換成靜態 JSON，供 Nginx 或簡易伺服器使用")
    print("=" * 80)

    # 設定路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # 上一層目錄
    base_dir = os.path.join(project_root, 'data')
    processed_data_dir = os.path.join(base_dir, 'processed_data')
    output_base_dir = os.path.join(project_root, 'frontend', 'static', 'api')

    # 掃描所有 Parquet 檔案
    parquet_pattern = os.path.join(processed_data_dir, '*', '*.parquet')
    parquet_files = glob.glob(parquet_pattern)

    print(f"\n找到 {len(parquet_files)} 個 Parquet 檔案")

    if not parquet_files:
        print("沒有找到任何 Parquet 檔案")
        return

    # 準備參數
    args_list = [(f, output_base_dir) for f in parquet_files]

    # 使用多進程處理
    max_workers = min(os.cpu_count() or 4, 8)
    print(f"使用 {max_workers} 個進程並行處理\n")

    start_time = time.time()

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_single_parquet, args_list))

    # 統計結果
    completed = sum(1 for r in results if '完成' in r)
    skipped = sum(1 for r in results if '跳過' in r)
    errors = sum(1 for r in results if '錯誤' in r)

    elapsed = time.time() - start_time

    print(f"\n{'=' * 80}")
    print(f"處理完成！")
    print(f"總計: {len(parquet_files)} 個檔案")
    print(f"完成: {completed} 個")
    print(f"跳過: {skipped} 個")
    print(f"錯誤: {errors} 個")
    print(f"耗時: {elapsed:.2f} 秒")
    print(f"輸出目錄: {output_base_dir}")
    print("=" * 80)

    # 顯示錯誤（如果有）
    error_results = [r for r in results if '錯誤' in r]
    if error_results:
        print("\n錯誤列表:")
        for err in error_results[:10]:  # 只顯示前 10 個
            print(f"  {err}")

if __name__ == "__main__":
    main()
