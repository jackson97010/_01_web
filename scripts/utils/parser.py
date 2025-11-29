"""
資料解析模組
包含所有 Quote 資料的解析函數
"""
import pandas as pd
from typing import Dict, Optional, Any
from .config import PRICE_DECIMAL_DIVISOR, TIMESTAMP_LENGTH, DATETIME_FORMAT


def parse_timestamp(timestamp_str: str, date_str: str) -> pd.Timestamp:
    """
    解析時間戳並轉換為 datetime

    時間戳格式: HHMMSSffffff (時分秒+微秒，共12位)

    Args:
        timestamp_str: 時間戳字串
        date_str: 日期字串 (YYYYMMDD)

    Returns:
        pandas Timestamp 對象
    """
    try:
        ts = str(timestamp_str).zfill(TIMESTAMP_LENGTH)
        dt_str = date_str + ts
        return pd.to_datetime(dt_str, format=DATETIME_FORMAT, errors='coerce')
    except Exception:
        return pd.NaT


def parse_trade_line(line: str, date_str: str) -> Optional[Dict[str, Any]]:
    """
    解析 Trade 資料行

    格式: Trade,股票代碼,成交時間,試撮旗標,成交價,成交單量,成交總量[,序號]
    - 試撮旗標: 0=一般揭示, 1=試算揭示
    - 成交價: 需除以 10000 (4位小數)

    Args:
        line: 原始資料行
        date_str: 日期字串 (YYYYMMDD)

    Returns:
        解析後的資料字典，失敗時返回 None
    """
    fields = line.strip().split(',')
    if len(fields) < 7:
        return None

    try:
        stock_code = fields[1].strip()
        timestamp = fields[2].strip()
        flag = int(fields[3])
        price_raw = int(fields[4])
        volume = int(fields[5])
        total_volume = int(fields[6])

        # 價格除以 10000（4位小數）
        price = price_raw / PRICE_DECIMAL_DIVISOR
        dt = parse_timestamp(timestamp, date_str)

        return {
            'Type': 'Trade',
            'StockCode': stock_code,
            'Datetime': dt,
            'Timestamp': int(timestamp) if timestamp.isdigit() else None,
            'Flag': flag,
            'Price': price,
            'Volume': volume,
            'TotalVolume': total_volume
        }
    except (ValueError, IndexError):
        return None


def parse_depth_line(line: str, date_str: str) -> Optional[Dict[str, Any]]:
    """
    解析 Depth 資料行

    格式: Depth,股票代碼,報價時間,BID:委買檔數,買盤檔位...,ASK:委賣檔數,賣盤檔位...[,序號]
    - 買賣盤檔位格式: 價格*數量
    - 價格: 需除以 10000 (4位小數)

    Args:
        line: 原始資料行
        date_str: 日期字串 (YYYYMMDD)

    Returns:
        解析後的資料字典，失敗時返回 None
    """
    fields = line.strip().split(',')
    if len(fields) < 4:
        return None

    try:
        stock_code = fields[1].strip()
        timestamp = fields[2].strip()

        # 尋找 BID 和 ASK 的位置
        bid_idx = -1
        ask_idx = -1
        bid_count = 0
        ask_count = 0

        for i, field in enumerate(fields):
            if 'BID:' in field:
                bid_idx = i
                bid_count = int(field.split(':')[1])
            elif 'ASK:' in field:
                ask_idx = i
                ask_count = int(field.split(':')[1])

        if bid_idx == -1 or ask_idx == -1:
            return None

        dt = parse_timestamp(timestamp, date_str)

        result = {
            'Type': 'Depth',
            'StockCode': stock_code,
            'Datetime': dt,
            'Timestamp': int(timestamp) if timestamp.isdigit() else None,
            'BidCount': bid_count,
            'AskCount': ask_count
        }

        # 解析買盤5檔
        bid_fields = fields[bid_idx+1:ask_idx]
        for i in range(5):
            price, volume = None, None
            if i < len(bid_fields) and i < bid_count and '*' in bid_fields[i]:
                price_str, volume_str = bid_fields[i].split('*')
                price = int(price_str) / PRICE_DECIMAL_DIVISOR
                volume = int(volume_str)
            result[f'Bid{i+1}_Price'] = price
            result[f'Bid{i+1}_Volume'] = volume

        # 解析賣盤5檔
        # 最後一個欄位可能是序號（不含 *），需要排除
        last_field = fields[-1]
        end_idx = -1 if '*' not in last_field else None
        ask_fields = fields[ask_idx+1:end_idx] if end_idx else fields[ask_idx+1:]

        for i in range(5):
            price, volume = None, None
            if i < len(ask_fields) and i < ask_count and '*' in ask_fields[i]:
                price_str, volume_str = ask_fields[i].split('*')
                price = int(price_str) / PRICE_DECIMAL_DIVISOR
                volume = int(volume_str)
            result[f'Ask{i+1}_Price'] = price
            result[f'Ask{i+1}_Volume'] = volume

        return result

    except (ValueError, IndexError):
        return None


def split_price_volume(value: str) -> tuple[Optional[float], Optional[int]]:
    """
    拆分價格*數量的字串

    Args:
        value: 價格*數量字串

    Returns:
        (價格, 數量) tuple，失敗時返回 (None, None)
    """
    if not value or '*' not in value:
        return None, None

    try:
        price_str, volume_str = value.split('*')
        price = int(price_str) / PRICE_DECIMAL_DIVISOR
        volume = int(volume_str)
        return price, volume
    except (ValueError, TypeError):
        return None, None
