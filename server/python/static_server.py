"""
靜態檔案伺服器
使用 Python 內建的 http.server，效能遠超 Flask
直接服務預處理好的 JSON 檔案
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import sys
import json
from urllib.parse import unquote

class CORSHTTPRequestHandler(SimpleHTTPRequestHandler):
    """支援 CORS 的 HTTP 請求處理器"""

    def __init__(self, *args, **kwargs):
        # 設定工作目錄為專案根目錄（server/python 的上兩層）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        super().__init__(*args, directory=project_root, **kwargs)

    def end_headers(self):
        """添加 CORS 標頭"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # 快取 1 小時（歷史資料不會變）
        self.send_header('Cache-Control', 'public, max-age=3600')
        super().end_headers()

    def do_OPTIONS(self):
        """處理 CORS 預檢請求"""
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        """處理 GET 請求"""
        # 解析路徑
        path = unquote(self.path)

        # 根路徑重定向到 index.html
        if path == '/':
            path = '/index.html'

        # API 路由：/api/data/{date}/{stock_code}
        if path.startswith('/api/data/'):
            parts = path.split('/')
            if len(parts) >= 5:
                date = parts[3]
                stock_code = parts[4]

                # 對應到靜態 JSON 檔案
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(script_dir))
                json_path = os.path.join(
                    project_root,
                    'frontend', 'static', 'api', date, f'{stock_code}.json'
                )

                if os.path.exists(json_path):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()

                    with open(json_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return
                else:
                    self.send_error(404, json.dumps({'error': '找不到資料'}))
                    return

        # API 路由：/api/dates
        elif path == '/api/dates':
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(script_dir))
            static_api_dir = os.path.join(
                project_root,
                'frontend', 'static', 'api'
            )

            if os.path.exists(static_api_dir):
                dates = [d for d in os.listdir(static_api_dir)
                        if os.path.isdir(os.path.join(static_api_dir, d)) and d.isdigit()]
                dates.sort(reverse=True)

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(dates).encode())
                return
            else:
                self.send_error(404, json.dumps({'error': '找不到資料目錄'}))
                return

        # API 路由：/api/stocks/{date}
        elif path.startswith('/api/stocks/'):
            parts = path.split('/')
            if len(parts) >= 4:
                date = parts[3]

                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(script_dir))
                date_dir = os.path.join(
                    project_root,
                    'frontend', 'static', 'api', date
                )

                if os.path.exists(date_dir):
                    stocks = [os.path.splitext(f)[0] for f in os.listdir(date_dir)
                             if f.endswith('.json')]
                    stocks.sort()

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(stocks).encode())
                    return
                else:
                    self.send_error(404, json.dumps({'error': '找不到該日期'}))
                    return

        # 其他請求使用預設處理（靜態檔案）
        super().do_GET()

    def log_message(self, format, *args):
        """自訂日誌格式"""
        sys.stdout.write("%s - - [%s] %s\n" %
                        (self.address_string(),
                         self.log_date_time_string(),
                         format % args))

def run_server(port=5000):
    """啟動伺服器"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSHTTPRequestHandler)

    print("=" * 80)
    print("靜態檔案伺服器（高效能版本）")
    print("=" * 80)
    print(f"伺服器啟動於: http://localhost:{port}")
    print(f"API 端點:")
    print(f"  - http://localhost:{port}/api/dates")
    print(f"  - http://localhost:{port}/api/stocks/{{date}}")
    print(f"  - http://localhost:{port}/api/data/{{date}}/{{stock_code}}")
    print(f"前端頁面:")
    print(f"  - http://localhost:{port}/")
    print(f"  - http://localhost:{port}/index.html")
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

    parser = argparse.ArgumentParser(description='靜態檔案伺服器')
    parser.add_argument('--port', type=int, default=5000, help='伺服器埠號 (預設: 5000)')

    args = parser.parse_args()
    run_server(args.port)
