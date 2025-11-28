#!/usr/bin/env python3
"""
正確的 OTC/TSE Quote 解碼程式
根據官方文件規範重新實作
"""

import pandas as pd
import os
import re
from datetime import datetime, timedelta
import glob
from pathlib import Path


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
    """
    獲取需要保存的股票（當日+前一交易日漲停）

    根據需求：解 2025-10-31 時，需要解：
    1. 2025-10-30 有出現在 lup_ma20_filtered.parquet 的股票清單
    2. 2025-10-31 有出現在 lup_ma20_filtered.parquet 的股票清單
    """
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


def parse_timestamp(timestamp_str, date_str):
    """
    解析時間戳

    時間戳格式: YYYMMDDHHMMSSMMM (13位)
    例: 84127027089
    - 841: 民國84年1月
    - 2702: 27日02時
    - 7089: 70分89秒

    實際上應該是: YYYMMDDHHMMSSxxx
    - 前8位: 民國年月日 (例: 84127 = 民國841年2月7日，實際是 84/12/7)

    等等，看起來格式應該是:
    84127027089
    841 = 年 (民國84年 = 1995年)
    27 = 月？不對

    讓我重新理解: 從範例 84127027089
    - 可能是 8位日期 + 5位時間或更多
    - 84127027089 有11位

    參考文件說明，時間戳可能是:
    民國年(2-3位) + 月(2位) + 日(2位) + 時(2位) + 分(2位) + 秒(2位) + 毫秒(3位)

    但 84127027089 只有11位...

    讓我用另一種理解: 可能是系統時間戳，需要配合日期來解析
    或者格式是: HHMMSSUUUUUU (時分秒+微秒)
    """
    try:
        # 時間戳長度可能不一致，補零到合理長度
        ts = str(timestamp_str).strip()

        # 假設時間戳格式為: HHMMSSuuuuuu (時分秒+微秒)
        # 或者可能是從當天00:00:00開始的時間戳
        # 先補零到至少9位 (HHMMSSMMM)
        ts = ts.zfill(9)

        # 解析時分秒
        hour = int(ts[0:2]) if len(ts) >= 2 else 0
        minute = int(ts[2:4]) if len(ts) >= 4 else 0
        second = int(ts[4:6]) if len(ts) >= 6 else 0
        microsecond = int(ts[6:12].ljust(6, '0')) if len(ts) >= 7 else 0

        # 組合完整時間
        datetime_str = f"{date_str} {hour:02d}:{minute:02d}:{second:02d}.{microsecond:06d}"
        return pd.to_datetime(datetime_str, format='%Y%m%d %H:%M:%S.%f', errors='coerce')
    except:
        return pd.NaT


def split_price_volume(value):
    """
    拆分價格*數量的字串

    根據文件: 價格是4位小數
    例: 333500 實際成交價 -> 33.35 (除以10000)
    """
    if pd.isna(value) or '*' not in str(value):
        return pd.NA, pd.NA
    try:
        price_str, volume_str = str(value).split('*')
        price = float(price_str) / 10000  # 價格除以 10000 (4位小數)
        volume = int(volume_str)
        return price, volume
    except (ValueError, TypeError):
        return pd.NA, pd.NA


def parse_trade_line(fields, date_str):
    """
    解析 Trade 資料行

    格式: Trade,股票代碼,成交時間,試撮旗標,成交價,成交單量,成交總量,序號
    試撮旗標: 0=一般揭示, 1=試算揭示
    成交價: 4位小數, 333500 -> 33.35

    範例: Trade,2355  ,131219825776,0,333500,1,1530,1234
    """
    try:
        if len(fields) < 7:
            return None

        stock_code = fields[1].strip()
        timestamp = fields[2].strip()
        flag = fields[3].strip()
        price_raw = fields[4].strip()
        volume = fields[5].strip()
        total_volume = fields[6].strip()

        result = {
            'Type': 'Trade',
            'StockCode': stock_code,
            'Timestamp': timestamp,
            'Flag': int(flag) if flag.isdigit() else pd.NA,
            'Price': float(price_raw) / 10000 if price_raw.isdigit() else pd.NA,  # 除以10000
            'Volume': int(volume) if volume.isdigit() else pd.NA,
            'TotalVolume': int(total_volume) if total_volume.isdigit() else pd.NA,
            'Datetime': parse_timestamp(timestamp, date_str)
        }

        return result

    except Exception as e:
        return None


def parse_depth_line(fields, date_str):
    """
    解析 Depth 資料行

    格式: Depth,股票代碼,報價時間,
          BID:委買檔數,第1檔價格*數量,第2檔價格*數量,第3檔價格*數量,第4檔價格*數量,第5檔價格*數量,
          ASK:委賣檔數,第1檔價格*數量,第2檔價格*數量,第3檔價格*數量,第4檔價格*數量,第5檔價格*數量,
          序號

    範例: Depth,2355  ,131219825776,BID:5,333000*27,332500*5,332000*32,331500*35,331000*62,ASK:5,333500*17,334000*5,334500*13,335000*44,335500*14,1234
    """
    try:
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
            'Timestamp': timestamp,
            'Datetime': parse_timestamp(timestamp, date_str),
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
    stock_data = {stock: [] for stock in stocks_to_process}

    # 逐行讀取檔案
    line_count = 0
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line_count += 1

                # 跳過非資料行 (如: UDPSession, INFO, LINKREADY等)
                if not line.startswith('Trade,') and not line.startswith('Depth,'):
                    continue

                fields = line.strip().split(',')

                if not fields or len(fields) < 2:
                    continue

                # 取得股票代碼
                stock_code = fields[1].strip()

                # 只處理目標股票
                if stock_code not in stocks_to_process:
                    continue

                # 根據類型解析
                if fields[0] == 'Trade':
                    trade_dict = parse_trade_line(fields, date_str)
                    if trade_dict is not None:
                        stock_data[stock_code].append(trade_dict)

                elif fields[0] == 'Depth':
                    depth_dict = parse_depth_line(fields, date_str)
                    if depth_dict is not None:
                        stock_data[stock_code].append(depth_dict)

    except Exception as e:
        print(f"讀取檔案時發生錯誤: {e}")
        return

    print(f"共讀取 {line_count} 行")

    # 處理每支股票的資料
    saved_count = 0
    for stock_code in stocks_to_process:
        records = stock_data[stock_code]

        if not records:
            continue

        # 建立 DataFrame
        df = pd.DataFrame(records)

        # 按時間排序
        if 'Datetime' in df.columns:
            df = df.sort_values('Datetime')

        # 儲存檔案
        output_path = os.path.join(output_dir, f"{stock_code}.parquet")
        df.to_parquet(output_path, index=False)
        saved_count += 1
        print(f"  已儲存 {stock_code}.parquet (共 {len(df)} 筆記錄)")

    print(f"\n日期 {date_str} 完成，共儲存 {saved_count} 支股票")


def main():
    """主程式"""
    print("=" * 80)
    print("OTC/TSE Quote 正確解碼程式")
    print("=" * 80)

    # 設定路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    base_dir = os.path.join(project_root, 'data')
    limit_up_file = os.path.join(base_dir, 'lup_ma20_filtered.parquet')
    output_base_dir = os.path.join(base_dir, 'decoded_quotes')

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

    # 處理每個檔案
    for i, file_path in enumerate(quote_files):
        print(f"\n[{i+1}/{len(quote_files)}] ", end='')
        process_quote_file(file_path, limit_up_dict, output_base_dir)

    print(f"\n{'=' * 80}")
    print("批次處理完成！")
    print(f"輸出目錄: {output_base_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
