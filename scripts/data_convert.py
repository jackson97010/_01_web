#!/usr/bin/env python3
"""
Parquet 轉 JSON 資料轉換程式（優化版）
將解碼後的 Parquet 檔案轉換為前端所需的 JSON 格式

特色：
- 模組化設計
- 多進程並行處理
- 自動跳過已轉換檔案
- 完整的資料處理（VWAP、內外盤判斷、統計資料）
"""
import pandas as pd
import os
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import time
from typing import Dict, List, Optional, Any

from utils import setup_logger
from utils.config import DECODED_DIR, OUTPUT_DIR, DEFAULT_MAX_WORKERS


def calculate_vwap(prices: List[float], volumes: List[int]) -> List[float]:
    """
    計算 VWAP（成交量加權平均價）

    Args:
        prices: 價格列表
        volumes: 成交量列表

    Returns:
        VWAP 列表
    """
    vwap = []
    cumulative_amount = 0.0
    cumulative_volume = 0

    for price, volume in zip(prices, volumes):
        cumulative_amount += price * volume
        cumulative_volume += volume
        if cumulative_volume > 0:
            vwap.append(cumulative_amount / cumulative_volume)
        else:
            vwap.append(0.0)

    return vwap


def determine_inner_outer(trade_price: float, prev_bid1: Optional[float], prev_ask1: Optional[float]) -> str:
    """
    判斷內外盤

    Args:
        trade_price: 成交價
        prev_bid1: 前一檔買1價
        prev_ask1: 前一檔賣1價

    Returns:
        '外'（外盤）、'內'（內盤）或 '–'（平盤）
    """
    if prev_ask1 is not None and trade_price >= prev_ask1:
        return '外'
    elif prev_bid1 is not None and trade_price <= prev_bid1:
        return '內'
    elif prev_bid1 is not None and prev_ask1 is not None:
        mid_price = (prev_bid1 + prev_ask1) / 2
        return '內' if trade_price <= mid_price else '外'
    return '–'


def prepare_chart_data(trade_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """準備圖表資料"""
    if trade_df.empty:
        return None

    trade_df = trade_df.sort_values('Datetime').reset_index(drop=True)

    timestamps = [str(ts) for ts in trade_df['Datetime']]
    prices = [float(p) if pd.notna(p) else 0.0 for p in trade_df['Price']]
    volumes = [int(v) if pd.notna(v) else 0 for v in trade_df['Volume']]

    # 計算累計成交量
    total_volumes = []
    cumsum = 0
    for v in volumes:
        cumsum += v
        total_volumes.append(cumsum)

    # 計算 VWAP
    vwap = calculate_vwap(prices, volumes)

    return {
        'timestamps': timestamps,
        'prices': prices,
        'volumes': volumes,
        'total_volumes': total_volumes,
        'vwap': vwap
    }


def prepare_depth_data(depth_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """準備當前五檔資料（取最新一筆）"""
    if depth_df.empty:
        return None

    depth_df = depth_df.sort_values('Datetime', ascending=False)
    latest = depth_df.iloc[0]

    bids = []
    asks = []

    for i in range(1, 6):
        # 買盤
        bid_price = latest.get(f'Bid{i}_Price')
        bid_volume = latest.get(f'Bid{i}_Volume')
        if pd.notna(bid_price) and pd.notna(bid_volume):
            bids.append({
                'price': float(bid_price),
                'volume': int(bid_volume)
            })

        # 賣盤
        ask_price = latest.get(f'Ask{i}_Price')
        ask_volume = latest.get(f'Ask{i}_Volume')
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


def prepare_depth_history(depth_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """準備五檔歷史資料"""
    if depth_df.empty:
        return []

    depth_df = depth_df.sort_values('Datetime').reset_index(drop=True)

    history = []
    for _, row in depth_df.iterrows():
        entry = {
            'timestamp': str(row['Datetime']),
            'bids': [],
            'asks': []
        }

        for i in range(1, 6):
            # 買盤
            bid_price = row.get(f'Bid{i}_Price')
            bid_volume = row.get(f'Bid{i}_Volume')
            if pd.notna(bid_price) and pd.notna(bid_volume):
                entry['bids'].append({
                    'price': float(bid_price),
                    'volume': int(bid_volume)
                })

            # 賣盤
            ask_price = row.get(f'Ask{i}_Price')
            ask_volume = row.get(f'Ask{i}_Volume')
            if pd.notna(ask_price) and pd.notna(ask_volume):
                entry['asks'].append({
                    'price': float(ask_price),
                    'volume': int(ask_volume)
                })

        history.append(entry)

    return history


def prepare_trade_details(trade_df: pd.DataFrame, depth_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """準備成交明細（含內外盤判斷）"""
    if trade_df.empty:
        return []

    trade_df = trade_df.sort_values('Datetime', ascending=False).reset_index(drop=True)

    if not depth_df.empty:
        depth_df = depth_df.sort_values('Datetime')
    else:
        depth_df = pd.DataFrame()

    details = []
    for _, row in trade_df.iterrows():
        trade_time = row['Datetime']
        trade_price = float(row['Price']) if pd.notna(row['Price']) else 0.0

        # 判斷內外盤
        inner_outer = '–'
        if not depth_df.empty and trade_price > 0:
            prior_depths = depth_df[depth_df['Datetime'] <= trade_time]
            if not prior_depths.empty:
                closest_depth = prior_depths.iloc[-1]
                bid1_price = closest_depth.get('Bid1_Price')
                ask1_price = closest_depth.get('Ask1_Price')
                inner_outer = determine_inner_outer(trade_price, bid1_price, ask1_price)

        details.append({
            'time': str(trade_time) if pd.notna(trade_time) else '',
            'price': trade_price,
            'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
            'inner_outer': inner_outer,
            'flag': int(row['Flag']) if pd.notna(row['Flag']) else 0
        })

    return details


def calculate_statistics(trade_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """計算統計資料"""
    if trade_df.empty:
        return None

    trade_df = trade_df.sort_values('Datetime').reset_index(drop=True)

    valid_prices = trade_df['Price'].dropna()
    valid_volumes = trade_df['Volume'].dropna()

    if valid_prices.empty:
        return None

    open_price = float(valid_prices.iloc[0])
    current_price = float(valid_prices.iloc[-1])
    high_price = float(valid_prices.max())
    low_price = float(valid_prices.min())

    # 計算平均成交價（成交量加權）
    valid_df = trade_df[trade_df['Price'].notna() & trade_df['Volume'].notna()]
    if not valid_df.empty:
        total_amount = (valid_df['Price'] * valid_df['Volume']).sum()
        total_volume = valid_df['Volume'].sum()
        avg_price = float(total_amount / total_volume) if total_volume > 0 else 0.0
    else:
        avg_price = 0.0

    change = current_price - open_price
    change_pct = (change / open_price * 100) if open_price > 0 else 0.0

    return {
        'current_price': current_price,
        'open_price': open_price,
        'high_price': high_price,
        'low_price': low_price,
        'avg_price': avg_price,
        'total_volume': int(total_volume) if not valid_df.empty else 0,
        'trade_count': len(trade_df),
        'change': change,
        'change_pct': change_pct
    }


def process_stock_file(args: tuple) -> str:
    """
    處理單個股票的 Parquet 檔案並轉換為 JSON

    Args:
        args: (parquet_file_path, output_base_dir)

    Returns:
        處理結果訊息
    """
    parquet_file, output_base_dir = args

    try:
        # 解析路徑
        parquet_path = Path(parquet_file)
        date_str = parquet_path.parent.name
        stock_code = parquet_path.stem

        # 檢查輸出檔案是否已存在
        output_dir = output_base_dir / date_str
        output_file = output_dir / f"{stock_code}.json"

        if output_file.exists():
            # 比較修改時間
            if output_file.stat().st_mtime > parquet_path.stat().st_mtime:
                return f"跳過 {date_str}/{stock_code} (已存在)"

        # 讀取 Parquet
        df = pd.read_parquet(parquet_path)

        if df.empty:
            return f"警告 {date_str}/{stock_code} (無資料)"

        # 分離 Trade 和 Depth 資料
        trade_df = df[df['Type'] == 'Trade'].copy()
        depth_df = df[df['Type'] == 'Depth'].copy()

        # 準備所有資料
        chart_data = prepare_chart_data(trade_df)
        depth_data = prepare_depth_data(depth_df)
        depth_history = prepare_depth_history(depth_df)
        trade_details = prepare_trade_details(trade_df, depth_df)
        statistics = calculate_statistics(trade_df)

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

        # 建立輸出目錄並寫入 JSON
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(api_response, f, ensure_ascii=False, separators=(',', ':'))

        return f"完成 {date_str}/{stock_code}"

    except Exception as e:
        return f"錯誤 {parquet_file}: {e}"


def main():
    """主程式"""
    logger = setup_logger('data_convert')

    logger.info("=" * 80)
    logger.info("Parquet → JSON 資料轉換程式（優化版）")
    logger.info("=" * 80)

    if not DECODED_DIR.exists():
        logger.error(f"錯誤: 找不到解碼目錄 {DECODED_DIR}")
        logger.info("請先執行 batch_decode.py")
        return

    # 掃描所有 Parquet 檔案
    parquet_pattern = str(DECODED_DIR / '*' / '*.parquet')
    import glob
    parquet_files = glob.glob(parquet_pattern)

    logger.info(f"\n找到 {len(parquet_files)} 個 Parquet 檔案")

    if not parquet_files:
        logger.warning("沒有找到任何 Parquet 檔案")
        return

    # 準備參數
    args_list = [(f, OUTPUT_DIR) for f in parquet_files]

    # 使用多進程處理
    max_workers = DEFAULT_MAX_WORKERS
    logger.info(f"使用 {max_workers} 個進程並行處理\n")

    start_time = time.time()

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_stock_file, args_list))

    # 統計結果
    completed = sum(1 for r in results if '完成' in r)
    skipped = sum(1 for r in results if '跳過' in r)
    errors = sum(1 for r in results if '錯誤' in r)

    elapsed = time.time() - start_time

    logger.info(f"\n{'=' * 80}")
    logger.info(f"處理完成！")
    logger.info(f"總計: {len(parquet_files)} 個檔案")
    logger.info(f"完成: {completed} 個")
    logger.info(f"跳過: {skipped} 個")
    logger.info(f"錯誤: {errors} 個")
    logger.info(f"耗時: {elapsed:.2f} 秒")
    logger.info(f"輸出目錄: {OUTPUT_DIR}")
    logger.info("=" * 80)

    # 顯示錯誤（如果有）
    error_results = [r for r in results if '錯誤' in r]
    if error_results:
        logger.warning("\n錯誤列表:")
        for err in error_results[:10]:  # 只顯示前 10 個
            logger.warning(f"  {err}")


if __name__ == "__main__":
    main()
