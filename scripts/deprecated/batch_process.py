import pandas as pd
import os
import re
from datetime import datetime, timedelta
import glob
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

def load_limit_up_list(parquet_file):
    """載入漲停清單"""
    df = pd.read_parquet(parquet_file)
    # 將 date 轉換為字串格式 YYYYMMDD
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
    df['stock_id'] = df['stock_id'].astype(str).str.strip()

    # 建立日期到股票列表的映射
    date_stocks = {}
    for _, row in df.iterrows():
        date_str = row['date']
        stock_id = row['stock_id']
        if date_str not in date_stocks:
            date_stocks[date_str] = set()
        date_stocks[date_str].add(stock_id)

    return date_stocks

def get_target_stocks(limit_up_dict, current_date):
    """獲取需要保存的股票（當日+前一交易日漲停）"""
    target_stocks = set()

    # 當日漲停股票
    if current_date in limit_up_dict:
        target_stocks.update(limit_up_dict[current_date])

    # 前一交易日漲停股票
    # 向前找最多 7 天（考慮週末+連假），找到第一個有資料的交易日
    try:
        current_dt = datetime.strptime(current_date, '%Y%m%d')
        for days_back in range(1, 8):
            prev_date = (current_dt - timedelta(days=days_back)).strftime('%Y%m%d')
            if prev_date in limit_up_dict:
                target_stocks.update(limit_up_dict[prev_date])
                break  # 只要找到前一個交易日就停止
    except:
        pass

    return target_stocks

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

def parse_depth_line(fields, date_str):
    """解析單行 Depth 資料"""
    try:
        # Depth 格式: Depth,股票代碼,時間戳,BID:count,買盤檔位...,ASK:count,賣盤檔位...,序號
        if len(fields) < 4:
            return None

        stock_code = fields[1].strip()
        timestamp = fields[2].strip()

        # 找到 BID 和 ASK 的位置
        bid_idx = -1
        ask_idx = -1

        for i, field in enumerate(fields):
            if 'BID:' in field:
                bid_idx = i
            elif 'ASK:' in field:
                ask_idx = i

        if bid_idx == -1 or ask_idx == -1:
            return None

        # 解析 BID count
        bid_count_str = fields[bid_idx].split(':')[1]
        bid_count = int(bid_count_str) if bid_count_str.isdigit() else 0

        # 解析 ASK count
        ask_count_str = fields[ask_idx].split(':')[1]
        ask_count = int(ask_count_str) if ask_count_str.isdigit() else 0

        # 建立結果字典
        result = {
            'Type': 'Depth',
            'StockCode': stock_code,
            'Timestamp': int(timestamp) if timestamp.isdigit() else pd.NA,
            'BidCount': bid_count,
            'AskCount': ask_count
        }

        # 解析買盤檔位（BID 之後、ASK 之前）
        bid_fields = fields[bid_idx+1:ask_idx]
        for i in range(5):
            if i < len(bid_fields) and i < bid_count:
                price, volume = split_price_volume(bid_fields[i])
                result[f'Bid{i+1}_Price'] = price
                result[f'Bid{i+1}_Volume'] = volume
            else:
                result[f'Bid{i+1}_Price'] = pd.NA
                result[f'Bid{i+1}_Volume'] = pd.NA

        # 解析賣盤檔位（ASK 之後到倒數第二個欄位，最後一個是序號）
        ask_fields = fields[ask_idx+1:-1] if len(fields) > ask_idx+1 else []
        for i in range(5):
            if i < len(ask_fields) and i < ask_count:
                price, volume = split_price_volume(ask_fields[i])
                result[f'Ask{i+1}_Price'] = price
                result[f'Ask{i+1}_Volume'] = volume
            else:
                result[f'Ask{i+1}_Price'] = pd.NA
                result[f'Ask{i+1}_Volume'] = pd.NA

        # 添加 Datetime
        try:
            s = str(timestamp).zfill(12)
            result['Datetime'] = pd.to_datetime(date_str + s, format='%Y%m%d%H%M%S%f', errors='coerce')
        except:
            result['Datetime'] = pd.NaT

        return result

    except Exception as e:
        return None

def process_quote_file(file_path, limit_up_dict, output_base_dir):
    """處理單個 Quote 檔案"""
    print(f"\n處理檔案: {file_path}")

    # 從檔案名稱中提取日期
    match = re.search(r'(\d{8})', os.path.basename(file_path))
    if not match:
        print(f"無法從檔案名稱中提取日期: {file_path}")
        return

    date_str = match.group(1)
    print(f"日期: {date_str}")

    # 獲取需要保存的股票清單
    target_stocks = get_target_stocks(limit_up_dict, date_str)
    if not target_stocks:
        print(f"日期 {date_str} 沒有需要保存的股票")
        return

    print(f"需要保存的股票數量: {len(target_stocks)}")
    print(f"股票清單: {sorted(list(target_stocks))[:10]}..." if len(target_stocks) > 10 else f"股票清單: {sorted(list(target_stocks))}")

    # 建立輸出目錄
    output_dir = os.path.join(output_base_dir, date_str)
    os.makedirs(output_dir, exist_ok=True)

    # 檢查已存在的檔案，跳過不需要處理的股票
    stocks_to_process = set()
    skipped_count = 0
    for stock in target_stocks:
        output_path = os.path.join(output_dir, f"{stock}.parquet")
        if os.path.exists(output_path):
            skipped_count += 1
        else:
            stocks_to_process.add(stock)

    if skipped_count > 0:
        print(f"已存在 {skipped_count} 個檔案，將跳過處理")

    if not stocks_to_process:
        print(f"所有股票檔案已存在，跳過此日期")
        return

    print(f"需要處理的股票數量: {len(stocks_to_process)}")

    # 初始化資料容器
    stock_data = {stock: {'trade': [], 'depth': []} for stock in stocks_to_process}

    # 定義欄位名稱
    trade_columns = ['Type', 'StockCode', 'Timestamp', 'Flag', 'Price', 'Volume', 'TotalVolume']

    # 逐行讀取檔案
    line_count = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1
                fields = line.strip().split(',')

                if not fields or len(fields) < 2:
                    continue

                # 跳過非資料行
                if fields[0] not in ['Trade', 'Depth']:
                    continue

                # 取得股票代碼
                stock_code = fields[1].strip()

                # 只處理目標股票
                if stock_code not in stocks_to_process:
                    continue

                # 根據類型分類
                if fields[0] == 'Trade' and len(fields) >= 7:
                    # Trade 資料可能有 7 或 8 個欄位（最後一個是序號），只取前 7 個
                    stock_data[stock_code]['trade'].append(fields[:7])
                elif fields[0] == 'Depth':
                    # 使用新的解析函數解析 Depth 資料
                    depth_dict = parse_depth_line(fields, date_str)
                    if depth_dict is not None:
                        stock_data[stock_code]['depth'].append(depth_dict)

    except Exception as e:
        print(f"讀取檔案時發生錯誤: {e}")
        return

    print(f"共讀取 {line_count} 行")

    # 處理每支股票的資料
    saved_count = 0
    for stock_code in stocks_to_process:
        trade_data = stock_data[stock_code]['trade']
        depth_data = stock_data[stock_code]['depth']

        if not trade_data and not depth_data:
            continue

        # 建立 Trade DataFrame
        df_trade = None
        if trade_data:
            df_trade = pd.DataFrame(trade_data, columns=trade_columns)
            df_trade['StockCode'] = df_trade['StockCode'].str.strip()
            df_trade['Timestamp'] = pd.to_numeric(df_trade['Timestamp'], errors='coerce').astype('Int64')
            s = df_trade['Timestamp'].astype('Int64').astype(str).str.zfill(12)
            df_trade['Datetime'] = pd.to_datetime(date_str + s, format='%Y%m%d%H%M%S%f', errors='coerce')
            df_trade['Price'] = pd.to_numeric(df_trade['Price'], errors='coerce') / 10000
            numeric_cols = ['Flag', 'Volume', 'TotalVolume']
            for col in numeric_cols:
                df_trade[col] = pd.to_numeric(df_trade[col], errors='coerce')

        # 建立 Depth DataFrame
        df_depth = None
        if depth_data:
            try:
                # depth_data 現在已經是字典列表，直接建立 DataFrame
                df_depth = pd.DataFrame(depth_data)
            except Exception as e:
                print(f"處理 {stock_code} 的 Depth 資料時發生錯誤: {e}")
                df_depth = None

        # 合併資料
        if df_trade is not None and df_depth is not None:
            all_columns = sorted(list(set(df_trade.columns) | set(df_depth.columns)))
            for col in all_columns:
                if col not in df_trade.columns:
                    df_trade[col] = pd.NA
                if col not in df_depth.columns:
                    df_depth[col] = pd.NA
            df_trade = df_trade.reindex(columns=all_columns)
            df_depth = df_depth.reindex(columns=all_columns)
            stock_df = pd.concat([df_trade, df_depth], ignore_index=True)
        elif df_trade is not None:
            stock_df = df_trade
        elif df_depth is not None:
            stock_df = df_depth
        else:
            continue

        # 按時間排序
        if 'Datetime' in stock_df.columns:
            stock_df = stock_df.sort_values('Datetime')

        # 儲存檔案
        output_path = os.path.join(output_dir, f"{stock_code}.parquet")
        stock_df.to_parquet(output_path, index=False)
        saved_count += 1
        print(f"  已儲存 {stock_code}.parquet (共 {len(stock_df)} 筆記錄)")

    print(f"\n日期 {date_str} 完成，共儲存 {saved_count} 支股票")

def main():
    """主程式"""
    print("=" * 80)
    print("OTC/TSE Quote 批次處理程式（多線程版本）")
    print("=" * 80)

    # 設定路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # 上一層目錄
    base_dir = os.path.join(project_root, 'data')
    limit_up_file = os.path.join(base_dir, 'lup_ma20_filtered.parquet')
    output_base_dir = os.path.join(base_dir, 'processed_data')

    # 檢查漲停清單檔案
    if not os.path.exists(limit_up_file):
        print(f"錯誤：找不到漲停清單檔案 {limit_up_file}")
        return

    # 載入漲停清單
    print(f"\n載入漲停清單: {limit_up_file}")
    limit_up_dict = load_limit_up_list(limit_up_file)
    print(f"共載入 {len(limit_up_dict)} 個日期的漲停資料")

    # 掃描所有 Quote 檔案
    quote_files = []
    for pattern in ['OTCQuote.*', 'TSEQuote.*']:
        files = glob.glob(os.path.join(base_dir, pattern))
        # 過濾出符合日期格式的檔案
        files = [f for f in files if re.search(r'\d{8}$', os.path.basename(f))]
        quote_files.extend(files)

    quote_files.sort()
    print(f"\n找到 {len(quote_files)} 個 Quote 檔案")

    if not quote_files:
        print("沒有找到 Quote 檔案")
        return

    # 預先檢查哪些日期已經完全處理完畢
    files_to_process = []
    for file_path in quote_files:
        match = re.search(r'(\d{8})', os.path.basename(file_path))
        if not match:
            continue

        date_str = match.group(1)
        target_stocks = get_target_stocks(limit_up_dict, date_str)

        if not target_stocks:
            continue

        # 檢查是否所有股票檔案都已存在
        output_dir = os.path.join(output_base_dir, date_str)
        all_exist = True
        if os.path.exists(output_dir):
            for stock in target_stocks:
                if not os.path.exists(os.path.join(output_dir, f"{stock}.parquet")):
                    all_exist = False
                    break
        else:
            all_exist = False

        if not all_exist:
            files_to_process.append(file_path)
        else:
            print(f"日期 {date_str} 所有檔案已存在，跳過")

    if not files_to_process:
        print("\n所有檔案都已處理完成！")
        return

    print(f"\n需要處理 {len(files_to_process)} 個檔案")

    # 使用多線程處理（建議使用 CPU 核心數）
    max_workers = min(4, os.cpu_count() or 4)  # 最多 4 個線程
    print(f"使用 {max_workers} 個線程並行處理")

    # 用於線程安全的計數器
    completed = {'count': 0}
    lock = threading.Lock()

    def process_with_progress(file_path):
        """帶進度顯示的處理函數"""
        try:
            process_quote_file(file_path, limit_up_dict, output_base_dir)
            with lock:
                completed['count'] += 1
                print(f"\n[進度: {completed['count']}/{len(files_to_process)}] 完成")
            return True
        except Exception as e:
            print(f"\n處理 {file_path} 時發生錯誤: {e}")
            return False

    # 執行多線程處理
    print("\n開始處理...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_with_progress, f) for f in files_to_process]

        # 等待所有任務完成
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"執行錯誤: {e}")

    print(f"\n{'=' * 80}")
    print("批次處理完成！")
    print(f"輸出目錄: {output_base_dir}")
    print("=" * 80)

if __name__ == "__main__":
    main()
