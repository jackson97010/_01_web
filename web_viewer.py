from flask import Flask, render_template, jsonify, request
import pandas as pd
import os
import glob
from datetime import datetime

app = Flask(__name__)

# 設定資料目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'processed_data')

def get_available_dates():
    """獲取所有可用的日期"""
    if not os.path.exists(DATA_DIR):
        return []

    dates = []
    for entry in os.listdir(DATA_DIR):
        path = os.path.join(DATA_DIR, entry)
        if os.path.isdir(path) and entry.isdigit() and len(entry) == 8:
            dates.append(entry)

    return sorted(dates, reverse=True)

def get_available_stocks(date):
    """獲取指定日期的所有股票"""
    date_dir = os.path.join(DATA_DIR, date)
    if not os.path.exists(date_dir):
        return []

    stocks = []
    for file in glob.glob(os.path.join(date_dir, '*.parquet')):
        stock_code = os.path.splitext(os.path.basename(file))[0]
        stocks.append(stock_code)

    return sorted(stocks)

def load_stock_data(date, stock_code):
    """載入股票資料"""
    file_path = os.path.join(DATA_DIR, date, f"{stock_code}.parquet")
    if not os.path.exists(file_path):
        return None

    try:
        df = pd.read_parquet(file_path)
        return df
    except Exception as e:
        print(f"載入資料錯誤: {e}")
        return None

def prepare_chart_data(df):
    """準備圖表資料"""
    if df is None or df.empty:
        return None

    # 只處理 Trade 資料用於走勢圖
    trade_df = df[df['Type'] == 'Trade'].copy()

    if trade_df.empty:
        return None

    # 確保有 Datetime 欄位
    if 'Datetime' not in trade_df.columns:
        return None

    # 按時間排序
    trade_df = trade_df.sort_values('Datetime')

    # 將 Datetime 轉換為 datetime 類型（如果還不是）
    if not pd.api.types.is_datetime64_any_dtype(trade_df['Datetime']):
        trade_df['Datetime'] = pd.to_datetime(trade_df['Datetime'])

    # 過濾盤前成交量（08:45~08:59）：將這段時間的成交量設為 0
    # 盤前試撮合不算真正的交易量
    def filter_premarket_volume(row):
        time = row['Datetime']
        if time.hour == 8 and 45 <= time.minute <= 59:
            return 0
        return row['Volume']

    trade_df['FilteredVolume'] = trade_df.apply(filter_premarket_volume, axis=1)

    # 只保留 09:00 以後的資料（正式交易時段）
    # 這樣成交明細可以從 09:00 roll 到 13:30，並顯示每分鐘內的所有 tick 變化
    trade_df_market = trade_df[trade_df['Datetime'].dt.hour >= 9].copy()

    if trade_df_market.empty:
        return None

    # 計算 VWAP（成交量加權平均價）
    # 針對每一筆 tick 計算累積 VWAP
    vwap_values = []
    cumulative_pv = 0  # 累積的 價格*成交量
    cumulative_volume = 0  # 累積成交量

    for idx, row in trade_df_market.iterrows():
        price = row['Price'] if pd.notna(row['Price']) else 0
        volume = row['FilteredVolume'] if pd.notna(row['FilteredVolume']) else 0

        cumulative_pv += price * volume
        cumulative_volume += volume

        if cumulative_volume > 0:
            vwap = cumulative_pv / cumulative_volume
        else:
            vwap = price

        vwap_values.append(vwap)

    # 準備時間序列資料（包含所有 tick）
    # 前端會根據這些資料顯示：
    # 1. 完整視圖：每分鐘的收盤價
    # 2. 回放模式：顯示當前時間之前的所有 tick（包括分鐘內跳動）
    chart_data = {
        'timestamps': trade_df_market['Datetime'].astype(str).tolist(),
        'prices': trade_df_market['Price'].fillna(0).tolist(),
        'volumes': trade_df_market['FilteredVolume'].fillna(0).tolist(),
        'total_volumes': trade_df_market['TotalVolume'].fillna(0).tolist(),
        'vwap': vwap_values  # VWAP 資料
    }

    return chart_data

def prepare_depth_data(df):
    """準備五檔資料（取最新一筆）"""
    if df is None or df.empty:
        return None

    # 只處理 Depth 資料
    depth_df = df[df['Type'] == 'Depth'].copy()

    if depth_df.empty:
        return None

    # 取最新一筆
    depth_df = depth_df.sort_values('Datetime', ascending=False)
    latest = depth_df.iloc[0]

    # 準備買賣五檔
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
    """準備五檔歷史資料（所有五檔變化，用於回放）"""
    if df is None or df.empty:
        return []

    # 只處理 Depth 資料
    depth_df = df[df['Type'] == 'Depth'].copy()

    if depth_df.empty:
        return []

    # 確保有 Datetime 欄位
    if 'Datetime' not in depth_df.columns:
        return []

    # 將 Datetime 轉換為 datetime 類型
    if not pd.api.types.is_datetime64_any_dtype(depth_df['Datetime']):
        depth_df['Datetime'] = pd.to_datetime(depth_df['Datetime'])

    # 只保留 09:00 以後的資料（正式交易時段）
    depth_df = depth_df[depth_df['Datetime'].dt.hour >= 9].copy()

    # 按時間排序（時間正序：09:00 -> 13:30）
    depth_df = depth_df.sort_values('Datetime')

    history = []
    for _, row in depth_df.iterrows():
        entry = {
            'timestamp': str(row['Datetime']),
            'bids': [],
            'asks': []
        }

        # 收集買賣五檔
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

def prepare_trade_details(df, limit=None):
    """準備成交明細（所有交易資料，用於回放）"""
    if df is None or df.empty:
        return []

    # 只處理 Trade 資料
    trade_df = df[df['Type'] == 'Trade'].copy()

    if trade_df.empty:
        return []

    # 確保有 Datetime 欄位
    if 'Datetime' not in trade_df.columns:
        return []

    # 將 Datetime 轉換為 datetime 類型
    if not pd.api.types.is_datetime64_any_dtype(trade_df['Datetime']):
        trade_df['Datetime'] = pd.to_datetime(trade_df['Datetime'])

    # 只保留 09:00 以後的交易（正式交易時段）
    trade_df = trade_df[trade_df['Datetime'].dt.hour >= 9].copy()

    # 準備 Depth 資料用於判斷內外盤
    depth_df = df[df['Type'] == 'Depth'].copy()
    if not depth_df.empty and 'Datetime' in depth_df.columns:
        if not pd.api.types.is_datetime64_any_dtype(depth_df['Datetime']):
            depth_df['Datetime'] = pd.to_datetime(depth_df['Datetime'])
        depth_df = depth_df[depth_df['Datetime'].dt.hour >= 9].copy()
        depth_df = depth_df.sort_values('Datetime')
    else:
        depth_df = pd.DataFrame()

    # 按時間降序排列（最新的在前，13:30 -> 09:00）
    trade_df = trade_df.sort_values('Datetime', ascending=False)

    # 如果有 limit，只取前 N 筆；否則返回所有資料
    if limit is not None and limit > 0:
        trade_df = trade_df.head(limit)

    details = []
    for _, row in trade_df.iterrows():
        trade_time = row['Datetime']
        trade_price = float(row['Price']) if pd.notna(row['Price']) else 0

        # 判斷內外盤：找到該成交時間之前最近的五檔資料
        inner_outer = '–'  # 預設值
        if not depth_df.empty and trade_price > 0:
            # 找到時間 <= trade_time 的最後一筆 Depth
            prior_depths = depth_df[depth_df['Datetime'] <= trade_time]
            if not prior_depths.empty:
                closest_depth = prior_depths.iloc[-1]

                # 取得買一和賣一價格
                bid1_price = closest_depth.get('Bid1_Price')
                ask1_price = closest_depth.get('Ask1_Price')

                # 判斷邏輯：
                # - 如果成交價 <= 買一價，為內盤（賣方主動，打到買盤）
                # - 如果成交價 >= 賣一價，為外盤（買方主動，打到賣盤）
                # - 否則無法判斷（可能在買賣價之間）
                if pd.notna(bid1_price) and trade_price <= bid1_price:
                    inner_outer = '內盤'
                elif pd.notna(ask1_price) and trade_price >= ask1_price:
                    inner_outer = '外盤'
                else:
                    # 如果成交價在買賣價之間，根據距離判斷
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

    # 確保有 Datetime 欄位
    if 'Datetime' not in trade_df.columns:
        return None

    # 將 Datetime 轉換為 datetime 類型
    if not pd.api.types.is_datetime64_any_dtype(trade_df['Datetime']):
        trade_df['Datetime'] = pd.to_datetime(trade_df['Datetime'])

    # 只取 09:00 以後的資料來計算統計（正式交易時段）
    trade_df_market = trade_df[trade_df['Datetime'].dt.hour >= 9].copy()

    if trade_df_market.empty:
        return None

    prices = trade_df_market['Price'].dropna()
    volumes = trade_df_market['Volume'].dropna()

    if prices.empty:
        return None

    # 計算均價：使用成交量加權平均價（VWAP）
    # 公式：Σ(價格 × 數量) / Σ(數量)
    # 這是每日開盤後累加每筆成交的價格乘上數量，除以累計的成交數量
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
        'avg_price': float(avg_price),  # 成交量加權平均價
        'total_volume': int(trade_df_market['TotalVolume'].max()) if 'TotalVolume' in trade_df_market else 0,
        'trade_count': len(trade_df_market)
    }

    # 計算漲跌
    if stats['open_price'] > 0:
        change = stats['current_price'] - stats['open_price']
        change_pct = (change / stats['open_price']) * 100
        stats['change'] = float(change)
        stats['change_pct'] = float(change_pct)
    else:
        stats['change'] = 0
        stats['change_pct'] = 0

    return stats

@app.route('/')
def index():
    """首頁"""
    return render_template('viewer.html')

@app.route('/api/dates')
def api_dates():
    """API: 獲取可用日期"""
    dates = get_available_dates()
    return jsonify(dates)

@app.route('/api/stocks/<date>')
def api_stocks(date):
    """API: 獲取指定日期的股票"""
    stocks = get_available_stocks(date)
    return jsonify(stocks)

@app.route('/api/data/<date>/<stock_code>')
def api_data(date, stock_code):
    """API: 獲取股票完整資料"""
    df = load_stock_data(date, stock_code)

    if df is None:
        return jsonify({'error': '找不到資料'}), 404

    # 準備各種資料
    chart_data = prepare_chart_data(df)
    depth_data = prepare_depth_data(df)  # 最新一筆五檔（用於靜態顯示）
    depth_history = prepare_depth_history(df)  # 完整五檔時間序列（用於回放）
    trade_details = prepare_trade_details(df)
    statistics = calculate_statistics(df)

    return jsonify({
        'chart': chart_data,
        'depth': depth_data,
        'depth_history': depth_history,  # 新增：五檔完整時間序列
        'trades': trade_details,
        'stats': statistics,
        'stock_code': stock_code,
        'date': date
    })

@app.route('/api/depth_history/<date>/<stock_code>')
def api_depth_history(date, stock_code):
    """API: 獲取五檔歷史變化"""
    df = load_stock_data(date, stock_code)

    if df is None:
        return jsonify({'error': '找不到資料'}), 404

    depth_df = df[df['Type'] == 'Depth'].copy()

    if depth_df.empty:
        return jsonify([])

    # 按時間排序
    depth_df = depth_df.sort_values('Datetime')

    history = []
    for _, row in depth_df.iterrows():
        entry = {
            'timestamp': str(row['Datetime']) if 'Datetime' in row else '',
            'bids': [],
            'asks': []
        }

        # 收集買賣五檔
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

    return jsonify(history)

if __name__ == '__main__':
    print("=" * 80)
    print("OTC/TSE Quote 網頁視覺化伺服器")
    print("=" * 80)
    print(f"資料目錄: {DATA_DIR}")
    print("啟動伺服器於 http://localhost:5000")
    print("=" * 80)
    app.run(debug=True, host='0.0.0.0', port=5000)
