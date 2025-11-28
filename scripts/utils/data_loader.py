"""
資料載入模組
處理漲停清單載入和目標股票篩選
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Set
from pathlib import Path


def load_limit_up_list(parquet_file: Path) -> Dict[str, Set[str]]:
    """
    載入漲停清單並建立日期到股票的映射

    Args:
        parquet_file: Parquet 檔案路徑

    Returns:
        日期到股票代碼集合的字典 {date_str: {stock_id, ...}}
    """
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


def get_target_stocks(limit_up_dict: Dict[str, Set[str]], current_date: str) -> Set[str]:
    """
    獲取需要解析的股票（當日 + 前一交易日漲停）

    根據需求：解 2025-10-31 時，需要解：
    1. 2025-10-31 有出現在 lup_ma20_filtered.parquet 的股票清單
    2. 2025-10-30 有出現在 lup_ma20_filtered.parquet 的股票清單（前一交易日）

    Args:
        limit_up_dict: 日期到股票集合的字典
        current_date: 當前日期 (YYYYMMDD)

    Returns:
        目標股票代碼集合
    """
    target_stocks = set()

    # 當日漲停股票
    if current_date in limit_up_dict:
        target_stocks.update(limit_up_dict[current_date])

    # 前一交易日漲停股票（向前找最多7天，考慮週末和連假）
    try:
        current_dt = datetime.strptime(current_date, '%Y%m%d')
        for days_back in range(1, 8):
            prev_date = (current_dt - timedelta(days=days_back)).strftime('%Y%m%d')
            if prev_date in limit_up_dict:
                target_stocks.update(limit_up_dict[prev_date])
                break  # 只要找到前一個交易日就停止
    except Exception:
        pass

    return target_stocks


def load_parquet_to_dataframe(parquet_path: Path) -> pd.DataFrame:
    """
    載入 Parquet 檔案為 DataFrame

    Args:
        parquet_path: Parquet 檔案路徑

    Returns:
        DataFrame
    """
    return pd.read_parquet(parquet_path)


def read_quote_file(file_path: Path, target_stocks: Set[str], date_str: str) -> Dict[str, list]:
    """
    讀取 Quote 檔案並解析指定股票的資料

    Args:
        file_path: Quote 檔案路徑
        target_stocks: 目標股票代碼集合
        date_str: 日期字串 (YYYYMMDD)

    Returns:
        股票代碼到記錄列表的字典 {stock_code: [record, ...]}
    """
    from .parser import parse_trade_line, parse_depth_line

    # 初始化資料容器
    stock_data = {stock: [] for stock in target_stocks}
    stats = {'trade': 0, 'depth': 0, 'error': 0}

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # 只處理 Trade 和 Depth 資料行
                if not line.startswith('Trade,') and not line.startswith('Depth,'):
                    continue

                fields = line.split(',')
                if len(fields) < 2:
                    continue

                stock_code = fields[1].strip()
                if stock_code not in target_stocks:
                    continue

                # 解析資料
                if line.startswith('Trade,'):
                    parsed = parse_trade_line(line, date_str)
                    if parsed:
                        stock_data[stock_code].append(parsed)
                        stats['trade'] += 1
                    else:
                        stats['error'] += 1

                elif line.startswith('Depth,'):
                    parsed = parse_depth_line(line, date_str)
                    if parsed:
                        stock_data[stock_code].append(parsed)
                        stats['depth'] += 1
                    else:
                        stats['error'] += 1

    except Exception as e:
        print(f"  讀取錯誤: {e}")
        return {}

    return stock_data, stats
