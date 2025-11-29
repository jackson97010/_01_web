"""
Parquet 資料伺服器
直接讀取 decoded_quotes 目錄下的 Parquet 檔案，即時轉換為 JSON
無需預先轉換，節省儲存空間
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import sys
import json
import pandas as pd
import numpy as np
from urllib.parse import unquote
from pathlib import Path


def determine_inner_outer(current_price, prev_bid1, prev_ask1):
    """判斷內外盤"""
    if prev_ask1 is not None and current_price >= prev_ask1:
        return '外'
    elif prev_bid1 is not None and current_price <= prev_bid1:
        return '內'
    else:
        return '–'


def convert_parquet_to_json(parquet_path):
    """將 Parquet 檔案轉換為 JSON 格式"""
    try:
        # 讀取 Parquet
        df = pd.read_parquet(parquet_path)

        if len(df) == 0:
            return None

        # 分離 Trade 和 Depth
        trade_df = df[df['Type'] == 'Trade'].copy()
        depth_df = df[df['Type'] == 'Depth'].copy()

        stock_code = df['StockCode'].iloc[0]
        date_str = df['Datetime'].iloc[0].strftime('%Y%m%d')

        # 處理 trades
        trades = []
        if len(trade_df) > 0:
            trade_df = trade_df.sort_values('Datetime', ascending=False).reset_index(drop=True)

            prev_bid1 = None
            prev_ask1 = None

            for idx, row in trade_df.iterrows():
                prev_depth = depth_df[depth_df['Datetime'] < row['Datetime']].tail(1)

                if len(prev_depth) > 0:
                    prev_bid1 = prev_depth.iloc[0].get('Bid1_Price')
                    prev_ask1 = prev_depth.iloc[0].get('Ask1_Price')

                inner_outer = determine_inner_outer(row['Price'], prev_bid1, prev_ask1)

                trades.append({
                    'time': row['Datetime'].strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'price': float(row['Price']),
                    'volume': int(row['Volume']),
                    'inner_outer': inner_outer,
                    'flag': int(row['Flag'])
                })

        # 處理 depth_history
        depth_history = []
        if len(depth_df) > 0:
            depth_df = depth_df.sort_values('Datetime').reset_index(drop=True)

            for _, row in depth_df.iterrows():
                bids = []
                asks = []

                for i in range(1, 6):
                    bid_price = row.get(f'Bid{i}_Price')
                    bid_volume = row.get(f'Bid{i}_Volume')
                    if pd.notna(bid_price) and pd.notna(bid_volume):
                        bids.append({
                            'price': float(bid_price),
                            'volume': int(bid_volume)
                        })

                for i in range(1, 6):
                    ask_price = row.get(f'Ask{i}_Price')
                    ask_volume = row.get(f'Ask{i}_Volume')
                    if pd.notna(ask_price) and pd.notna(ask_volume):
                        asks.append({
                            'price': float(ask_price),
                            'volume': int(ask_volume)
                        })

                depth_history.append({
                    'timestamp': row['Datetime'].strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'bids': bids,
                    'asks': asks
                })

        # 處理 depth（當前）
        depth = None
        if len(depth_history) > 0:
            latest_depth = depth_history[-1]
            depth = {
                'bids': latest_depth['bids'],
                'asks': latest_depth['asks'],
                'timestamp': latest_depth['timestamp']
            }

        # 處理 chart
        chart = None
        if len(trade_df) > 0:
            trade_df_asc = trade_df.sort_values('Datetime').reset_index(drop=True)

            timestamps = trade_df_asc['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S.%f').tolist()
            prices = trade_df_asc['Price'].astype(float).tolist()
            volumes = trade_df_asc['Volume'].astype(int).tolist()
            total_volumes = trade_df_asc['Volume'].cumsum().astype(int).tolist()

            trade_df_asc['cumulative_amount'] = (trade_df_asc['Price'] * trade_df_asc['Volume']).cumsum()
            trade_df_asc['cumulative_volume'] = trade_df_asc['Volume'].cumsum()
            vwap = (trade_df_asc['cumulative_amount'] / trade_df_asc['cumulative_volume']).astype(float).tolist()

            chart = {
                'timestamps': timestamps,
                'prices': prices,
                'volumes': volumes,
                'total_volumes': total_volumes,
                'vwap': vwap
            }

        # 處理 stats
        stats = None
        if len(trade_df) > 0:
            trade_df_asc = trade_df.sort_values('Datetime').reset_index(drop=True)

            open_price = float(trade_df_asc.iloc[0]['Price'])
            current_price = float(trade_df_asc.iloc[-1]['Price'])
            high_price = float(trade_df_asc['Price'].max())
            low_price = float(trade_df_asc['Price'].min())

            total_amount = (trade_df_asc['Price'] * trade_df_asc['Volume']).sum()
            total_volume = trade_df_asc['Volume'].sum()
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

        return {
            'chart': chart,
            'depth': depth,
            'depth_history': depth_history,
            'trades': trades,
            'stats': stats,
            'stock_code': stock_code,
            'date': date_str
        }

    except Exception as e:
        print(f"Error converting parquet: {e}")
        return None


class ParquetHTTPRequestHandler(BaseHTTPRequestHandler):
    """處理 HTTP 請求的處理器"""

    def __init__(self, *args, **kwargs):
        # 設定工作目錄
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(os.path.dirname(script_dir))
        self.decoded_dir = os.path.join(self.project_root, 'data', 'decoded_quotes')
        super().__init__(*args, **kwargs)

    def end_headers(self):
        """添加 CORS 標頭"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'public, max-age=3600')
        super().end_headers()

    def do_OPTIONS(self):
        """處理 CORS 預檢請求"""
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        """處理 GET 請求"""
        path = unquote(self.path)

        # 根路徑重定向
        if path == '/':
            path = '/index.html'

        # API: /api/dates
        if path == '/api/dates':
            if os.path.exists(self.decoded_dir):
                dates = [d for d in os.listdir(self.decoded_dir)
                        if os.path.isdir(os.path.join(self.decoded_dir, d)) and d.isdigit()]
                dates.sort(reverse=True)

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(dates).encode())
                return
            else:
                self.send_error(404, json.dumps({'error': '找不到資料目錄'}))
                return

        # API: /api/stocks/{date}
        elif path.startswith('/api/stocks/'):
            parts = path.split('/')
            if len(parts) >= 4:
                date = parts[3]
                date_dir = os.path.join(self.decoded_dir, date)

                if os.path.exists(date_dir):
                    stocks = [os.path.splitext(f)[0] for f in os.listdir(date_dir)
                             if f.endswith('.parquet')]
                    stocks.sort()

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(stocks).encode())
                    return
                else:
                    self.send_error(404, json.dumps({'error': '找不到該日期'}))
                    return

        # API: /api/data/{date}/{stock_code}
        elif path.startswith('/api/data/'):
            parts = path.split('/')
            if len(parts) >= 5:
                date = parts[3]
                stock_code = parts[4]

                parquet_path = os.path.join(self.decoded_dir, date, f'{stock_code}.parquet')

                if os.path.exists(parquet_path):
                    # 即時轉換 Parquet 為 JSON
                    data = convert_parquet_to_json(parquet_path)

                    if data:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
                        return
                    else:
                        self.send_error(500, json.dumps({'error': '資料轉換失敗'}))
                        return
                else:
                    self.send_error(404, json.dumps({'error': '找不到資料'}))
                    return

        # 靜態檔案服務
        # 嘗試從 frontend-app/dist 或 frontend 提供檔案
        for base_dir in ['frontend-app/dist', 'frontend']:
            file_path = os.path.join(self.project_root, base_dir, path.lstrip('/'))

            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.send_response(200)

                # 設定 Content-Type
                if file_path.endswith('.html'):
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                elif file_path.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript')
                elif file_path.endswith('.css'):
                    self.send_header('Content-type', 'text/css')
                elif file_path.endswith('.json'):
                    self.send_header('Content-type', 'application/json')
                else:
                    self.send_header('Content-type', 'application/octet-stream')

                self.end_headers()

                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
                return

        # 找不到檔案
        self.send_error(404, 'File not found')

    def log_message(self, format, *args):
        """自訂日誌格式"""
        sys.stdout.write("%s - [%s] %s\n" %
                        (self.address_string(),
                         self.log_date_time_string(),
                         format % args))


def run_server(port=5000):
    """啟動伺服器"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, ParquetHTTPRequestHandler)

    print("=" * 80)
    print("Parquet 資料伺服器（即時轉換版本）")
    print("=" * 80)
    print(f"伺服器啟動於: http://localhost:{port}")
    print(f"API 端點:")
    print(f"  - http://localhost:{port}/api/dates")
    print(f"  - http://localhost:{port}/api/stocks/{{date}}")
    print(f"  - http://localhost:{port}/api/data/{{date}}/{{stock_code}}")
    print(f"前端頁面:")
    print(f"  - http://localhost:{port}/")
    print("=" * 80)
    print("按 Ctrl+C 停止伺服器")
    print("=" * 80)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n正在關閉伺服器...")
        httpd.shutdown()
        print("伺服器已停止")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Parquet 資料伺服器')
    parser.add_argument('--port', type=int, default=5000, help='伺服器埠號 (預設: 5000)')

    args = parser.parse_args()
    run_server(args.port)
