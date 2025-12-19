#!/usr/bin/env python3
"""
Parquet 轉 JSON 轉換工具
將解碼後的 Parquet 檔案轉換為前端 JSON 格式

使用方式：
1. 批次模式（轉換所有檔案）：python convert.py
2. 單日模式（轉換特定日期）：python convert.py -d 20240101
3. 強制重新轉換：python convert.py -d 20240101 --force
"""
import pandas as pd
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import time
from typing import Dict, List, Optional, Any
import glob
import argparse

from utils import setup_logger
from utils.config import DECODED_DIR, OUTPUT_DIR, DEFAULT_MAX_WORKERS


def calculate_vwap_fast(prices: List[float], volumes: List[int]) -> List[float]:
    """快速計算 VWAP"""
    vwap = []
    cum_amount, cum_volume = 0.0, 0

    for p, v in zip(prices, volumes):
        cum_amount += p * v
        cum_volume += v
        vwap.append(cum_amount / cum_volume if cum_volume > 0 else 0.0)

    return vwap


def determine_inner_outer(price: float, bid1: Optional[float], ask1: Optional[float]) -> str:
    """判斷內外盤"""
    if ask1 is not None and price >= ask1:
        return '外'
    if bid1 is not None and price <= bid1:
        return '內'
    if bid1 is not None and ask1 is not None:
        return '內' if price <= (bid1 + ask1) / 2 else '外'
    return '–'


def prepare_chart_data(trade_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """準備圖表資料"""
    if trade_df.empty:
        return None

    trade_df = trade_df.sort_values('Datetime')

    timestamps = trade_df['Datetime'].astype(str).tolist()
    prices = trade_df['Price'].fillna(0).tolist()
    volumes = trade_df['Volume'].fillna(0).astype(int).tolist()

    # 累計成交量
    total_volumes = trade_df['Volume'].fillna(0).cumsum().astype(int).tolist()

    # VWAP
    vwap = calculate_vwap_fast(prices, volumes)

    return {
        'timestamps': timestamps,
        'prices': prices,
        'volumes': volumes,
        'total_volumes': total_volumes,
        'vwap': vwap
    }


def prepare_depth_data(depth_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """準備當前五檔（最新）"""
    if depth_df.empty:
        return None

    latest = depth_df.sort_values('Datetime', ascending=False).iloc[0]

    bids = []
    asks = []

    for i in range(1, 6):
        # 買盤
        bp = latest.get(f'Bid{i}_Price')
        bv = latest.get(f'Bid{i}_Volume')
        if pd.notna(bp) and pd.notna(bv):
            bids.append({'price': float(bp), 'volume': int(bv)})

        # 賣盤
        ap = latest.get(f'Ask{i}_Price')
        av = latest.get(f'Ask{i}_Volume')
        if pd.notna(ap) and pd.notna(av):
            asks.append({'price': float(ap), 'volume': int(av)})

    return {
        'bids': bids,
        'asks': asks,
        'timestamp': str(latest['Datetime'])
    }


def prepare_depth_history(depth_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """準備五檔歷史"""
    if depth_df.empty:
        return []

    depth_df = depth_df.sort_values('Datetime')
    history = []

    for _, row in depth_df.iterrows():
        entry = {
            'timestamp': str(row['Datetime']),
            'bids': [],
            'asks': []
        }

        for i in range(1, 6):
            # 買盤
            bp = row.get(f'Bid{i}_Price')
            bv = row.get(f'Bid{i}_Volume')
            if pd.notna(bp) and pd.notna(bv):
                entry['bids'].append({'price': float(bp), 'volume': int(bv)})

            # 賣盤
            ap = row.get(f'Ask{i}_Price')
            av = row.get(f'Ask{i}_Volume')
            if pd.notna(ap) and pd.notna(av):
                entry['asks'].append({'price': float(ap), 'volume': int(av)})

        history.append(entry)

    return history


def prepare_trade_details(trade_df: pd.DataFrame, depth_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """準備成交明細（含內外盤）"""
    if trade_df.empty:
        return []

    trade_df = trade_df.sort_values('Datetime', ascending=False)
    depth_df = depth_df.sort_values('Datetime') if not depth_df.empty else pd.DataFrame()

    details = []
    for _, row in trade_df.iterrows():
        price = float(row['Price']) if pd.notna(row['Price']) else 0.0

        # 判斷內外盤
        inner_outer = '–'
        if not depth_df.empty and price > 0:
            prior = depth_df[depth_df['Datetime'] <= row['Datetime']]
            if not prior.empty:
                closest = prior.iloc[-1]
                bid1 = closest.get('Bid1_Price')
                ask1 = closest.get('Ask1_Price')
                inner_outer = determine_inner_outer(price, bid1, ask1)

        details.append({
            'time': str(row['Datetime']),
            'price': price,
            'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
            'inner_outer': inner_outer,
            'flag': int(row['Flag']) if pd.notna(row['Flag']) else 0
        })

    return details


def calculate_statistics(trade_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """計算統計資料"""
    if trade_df.empty:
        return None

    trade_df = trade_df.sort_values('Datetime')

    prices = trade_df['Price'].dropna()
    if prices.empty:
        return None

    open_price = float(prices.iloc[0])
    current_price = float(prices.iloc[-1])
    high_price = float(prices.max())
    low_price = float(prices.min())

    # 成交量加權平均價
    valid = trade_df[trade_df['Price'].notna() & trade_df['Volume'].notna()]
    if not valid.empty:
        total_amount = (valid['Price'] * valid['Volume']).sum()
        total_volume = valid['Volume'].sum()
        avg_price = float(total_amount / total_volume) if total_volume > 0 else 0.0
    else:
        avg_price = 0.0
        total_volume = 0

    change = current_price - open_price
    change_pct = (change / open_price * 100) if open_price > 0 else 0.0

    return {
        'current_price': current_price,
        'open_price': open_price,
        'high_price': high_price,
        'low_price': low_price,
        'avg_price': avg_price,
        'total_volume': int(total_volume),
        'trade_count': len(trade_df),
        'change': change,
        'change_pct': change_pct
    }


def process_stock_file(args: tuple) -> str:
    """處理單個股票檔案"""
    parquet_file, output_base_dir, force = args

    try:
        parquet_path = Path(parquet_file)
        date_str = parquet_path.parent.name
        stock_code = parquet_path.stem

        # 檢查輸出
        output_dir = output_base_dir / date_str
        output_file = output_dir / f"{stock_code}.json"

        if not force and output_file.exists():
            return f"跳過 {date_str}/{stock_code}"

        # 讀取資料
        df = pd.read_parquet(parquet_path)
        if df.empty:
            return f"警告 {date_str}/{stock_code} (無資料)"

        # 分離資料
        trade_df = df[df['Type'] == 'Trade']
        depth_df = df[df['Type'] == 'Depth']

        # 準備資料
        api_response = {
            'chart': prepare_chart_data(trade_df),
            'depth': prepare_depth_data(depth_df),
            'depth_history': prepare_depth_history(depth_df),
            'trades': prepare_trade_details(trade_df, depth_df),
            'stats': calculate_statistics(trade_df),
            'stock_code': stock_code,
            'date': date_str
        }

        # 保存（壓縮格式）
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(api_response, f, ensure_ascii=False, separators=(',', ':'))

        return f"完成 {date_str}/{stock_code}"

    except Exception as e:
        return f"錯誤 {parquet_file}: {e}"


def convert_files(parquet_files: List[str], output_dir: Path, force: bool, logger) -> None:
    """轉換檔案列表"""
    if not parquet_files:
        logger.warning("無檔案需處理")
        return

    logger.info(f"找到 {len(parquet_files)} 個 Parquet 檔案")

    # 準備參數
    args_list = [(f, output_dir, force) for f in parquet_files]

    # 多進程處理
    logger.info(f"使用 {DEFAULT_MAX_WORKERS} 個進程並行處理\n")

    start_time = time.time()

    with ProcessPoolExecutor(max_workers=DEFAULT_MAX_WORKERS) as executor:
        results = list(executor.map(process_stock_file, args_list))

    # 統計
    completed = sum(1 for r in results if '完成' in r)
    skipped = sum(1 for r in results if '跳過' in r)
    errors = sum(1 for r in results if '錯誤' in r)

    elapsed = time.time() - start_time

    logger.info(f"\n{'='*80}")
    logger.info("處理完成！")
    logger.info(f"總計: {len(parquet_files)} 個")
    logger.info(f"完成: {completed} 個")
    logger.info(f"跳過: {skipped} 個")
    logger.info(f"錯誤: {errors} 個")
    logger.info(f"耗時: {elapsed:.2f} 秒")
    logger.info(f"輸出: {output_dir}")
    logger.info("="*80)

    # 顯示錯誤
    if errors > 0:
        error_results = [r for r in results if '錯誤' in r][:10]
        logger.warning("\n錯誤列表:")
        for err in error_results:
            logger.warning(f"  {err}")


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description='Parquet 轉 JSON 轉換工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  批次模式（轉換所有檔案）:
    python convert.py

  單日模式（轉換特定日期）:
    python convert.py -d 20240101
    python convert.py --date 20240101

  強制重新轉換（忽略快取）:
    python convert.py -d 20240101 --force
    python convert.py --force

  自訂輸出目錄:
    python convert.py -d 20240101 -o ./my_output
        """
    )

    parser.add_argument('-d', '--date', help='指定日期 (YYYYMMDD)')
    parser.add_argument('-o', '--output', help=f'輸出目錄 (預設: {OUTPUT_DIR})')
    parser.add_argument('-f', '--force', action='store_true', help='強制重新轉換（忽略快取）')

    args = parser.parse_args()
    logger = setup_logger('convert')

    logger.info("="*80)
    logger.info("Parquet → JSON 轉換工具")
    logger.info("="*80)

    if not DECODED_DIR.exists():
        logger.error(f"錯誤: 找不到解碼目錄 {DECODED_DIR}")
        logger.info("請先執行 decode.py")
        return

    output_dir = Path(args.output) if args.output else OUTPUT_DIR

    # 單日模式
    if args.date:
        logger.info(f"\n單日模式 - 轉換日期: {args.date}")
        date_dir = DECODED_DIR / args.date

        if not date_dir.exists():
            logger.error(f"錯誤: 找不到日期目錄 {date_dir}")
            logger.info("請先執行 decode.py 解碼該日期的資料")
            return

        parquet_files = glob.glob(str(date_dir / '*.parquet'))
        logger.info(f"輸入目錄: {date_dir}")
        logger.info(f"輸出目錄: {output_dir}")

        convert_files(parquet_files, output_dir, args.force, logger)
        return

    # 批次模式
    logger.info("\n批次模式 - 轉換所有檔案")
    parquet_files = glob.glob(str(DECODED_DIR / '*' / '*.parquet'))
    logger.info(f"輸入目錄: {DECODED_DIR}")
    logger.info(f"輸出目錄: {output_dir}")

    convert_files(parquet_files, output_dir, args.force, logger)


if __name__ == "__main__":
    main()
