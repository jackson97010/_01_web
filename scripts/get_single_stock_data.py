"""
單一股票資料查詢工具

功能:
- 指定日期、市場(OTC/TSE)、股票代號，從原始 Quote 檔案中提取資料。
- 可選擇將結果輸出到控制台、儲存為 Parquet 或 JSON 檔案。

使用範例 (在終端機中):
1. 顯示結果到控制台:
   python get_single_stock_data.py 20251031 TSE 2330 --output console

2. 儲存為 Parquet 檔案:
   python get_single_stock_data.py 20251031 OTC 6488 --output parquet
   20251125 8042 --output parquet
   python get_single_stock_data.py 20251125 OTC 4939 --output parquet
   python get_single_stock_data.py 20251128 TSE 2485 --output parquet
   python get_single_stock_data.py 20251127 TSE 2634 --output parquet
   python get_single_stock_data.py 20251128 TSE 1303 --output parquet
   python get_single_stock_data.py 20251201 TSE 8039 --output parquet
   python get_single_stock_data.py 20251202 TSE 8110 --output parquet

3. 儲存為 JSON 檔案:
   python get_single_stock_data.py 20251031 TSE 2330 --output json
"""
import pandas as pd
import os
import argparse
import json

# 從 decode_quotes.py 複製核心解析函數
def parse_timestamp(timestamp_str, date_str):
    """解析時間戳並轉換為 datetime"""
    try:
        ts = str(timestamp_str).zfill(12)
        dt_str = date_str + ts
        return pd.to_datetime(dt_str, format='%Y%m%d%H%M%S%f', errors='coerce')
    except:
        return pd.NaT

def parse_trade_line(line, date_str):
    """解析 Trade 資料行"""
    fields = line.strip().split(',')
    if len(fields) < 7: return None
    try:
        return {
            'Type': 'Trade',
            'StockCode': fields[1].strip(),
            'Datetime': parse_timestamp(fields[2].strip(), date_str),
            'Timestamp': int(fields[2].strip()),
            'Flag': int(fields[3]),
            'Price': int(fields[4]) / 10000.0,
            'Volume': int(fields[5]),
            'TotalVolume': int(fields[6])
        }
    except (ValueError, IndexError): return None

def parse_depth_line(line, date_str):
    """解析 Depth 資料行"""
    fields = line.strip().split(',')
    if len(fields) < 4: return None
    try:
        bid_idx, ask_idx, bid_count, ask_count = -1, -1, 0, 0
        for i, field in enumerate(fields):
            if 'BID:' in field:
                bid_idx, bid_count = i, int(field.split(':')[1])
            elif 'ASK:' in field:
                ask_idx, ask_count = i, int(field.split(':')[1])
        if bid_idx == -1 or ask_idx == -1: return None

        result = {
            'Type': 'Depth',
            'StockCode': fields[1].strip(),
            'Datetime': parse_timestamp(fields[2].strip(), date_str),
            'Timestamp': int(fields[2].strip()),
            'BidCount': bid_count,
            'AskCount': ask_count
        }
        
        bid_fields = fields[bid_idx+1:ask_idx]
        for i in range(5):
            price, volume = (None, None)
            if i < len(bid_fields) and i < bid_count and '*' in bid_fields[i]:
                price_str, vol_str = bid_fields[i].split('*')
                price, volume = int(price_str) / 10000.0, int(vol_str)
            result[f'Bid{i+1}_Price'], result[f'Bid{i+1}_Volume'] = price, volume

        end_idx = -1 if '*' not in fields[-1] else None
        ask_fields = fields[ask_idx+1:end_idx] if end_idx else fields[ask_idx+1:]
        for i in range(5):
            price, volume = (None, None)
            if i < len(ask_fields) and i < ask_count and '*' in ask_fields[i]:
                price_str, vol_str = ask_fields[i].split('*')
                price, volume = int(price_str) / 10000.0, int(vol_str)
            result[f'Ask{i+1}_Price'], result[f'Ask{i+1}_Volume'] = price, volume
            
        return result
    except (ValueError, IndexError): return None

def main():
    parser = argparse.ArgumentParser(description="從原始 Quote 檔案中查詢單一股票的資料。")
    parser.add_argument("date", type=str, help="查詢日期 (格式: YYYYMMDD)")
    parser.add_argument("market", type=str, choices=['OTC', 'TSE'], help="市場別 (OTC 或 TSE)")
    parser.add_argument("stock_code", type=str, help="股票代號")
    parser.add_argument("--output", type=str, choices=['console', 'parquet', 'json'], default='console', help="輸出格式")
    args = parser.parse_args()

    print(f"查詢條件: 日期={args.date}, 市場={args.market}, 股票={args.stock_code}, 輸出={args.output}")

    # --- 設定路徑 ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.join(project_root, 'data')
    output_dir = os.path.join(project_root, 'data', 'single_query_results')
    os.makedirs(output_dir, exist_ok=True)

    # --- 尋找原始檔案 ---
    quote_file_path = os.path.join(data_dir, f"{args.market}Quote.{args.date}")
    if not os.path.exists(quote_file_path):
        print(f"\n錯誤: 找不到原始資料檔案: {quote_file_path}")
        return

    print(f"正在讀取檔案: {quote_file_path}")

    # --- 讀取並解析資料 ---
    records = []
    try:
        with open(quote_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # 快速過濾，只處理包含目標股票代號的行
                if f",{args.stock_code}" not in line:
                    continue

                parsed = None
                if line.startswith('Trade,'):
                    parsed = parse_trade_line(line, args.date)
                elif line.startswith('Depth,'):
                    parsed = parse_depth_line(line, args.date)
                
                if parsed and parsed['StockCode'] == args.stock_code:
                    records.append(parsed)
    except Exception as e:
        print(f"讀取或解析檔案時發生錯誤: {e}")
        return

    if not records:
        print(f"\n查詢完成，但在檔案中找不到股票 {args.stock_code} 的任何 Trade 或 Depth 資料。")
        return

    # --- 轉換為 DataFrame ---
    df = pd.DataFrame(records)
    if 'Datetime' in df.columns:
        df = df.sort_values('Datetime').reset_index(drop=True)

    print(f"\n查詢成功！共找到 {len(df)} 筆記錄 (Trade: {len(df[df['Type']=='Trade'])}, Depth: {len(df[df['Type']=='Depth'])}).")

    # --- 根據參數輸出結果 ---
    if args.output == 'console':
        print("\n--- 資料預覽 (前 10 筆) ---")
        print(df.head(10).to_string())
        print("\n--- 資料預覽 (後 10 筆) ---")
        print(df.tail(10).to_string())

    elif args.output == 'parquet':
        output_path = os.path.join(output_dir, f"{args.date}_{args.stock_code}.parquet")
        df.to_parquet(output_path, index=False)
        print(f"\n資料已儲存至: {output_path}")

    elif args.output == 'json':
        output_path = os.path.join(output_dir, f"{args.date}_{args.stock_code}.json")
        # 將 Datetime 轉換為字串以利 JSON 序列化
        df['Datetime'] = df['Datetime'].astype(str)
        df.to_json(output_path, orient='records', indent=2, force_ascii=False)
        print(f"\n資料已儲存至: {output_path}")

if __name__ == "__main__":
    main()
