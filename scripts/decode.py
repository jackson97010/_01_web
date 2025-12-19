#!/usr/bin/env python3
"""
Quote 檔案批次解碼工具
快速解碼 OTC/TSE Quote 檔案為 Parquet 格式

使用方式：
1. 批次模式（使用漲停清單）：python decode.py
2. 指定模式：python decode.py --date 20240101 --stocks 2330,2317 --market TSE
3. 互動模式：python decode.py --interactive
"""
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Set, Dict, List
import glob
import re
import argparse

from utils import parse_trade_line, parse_depth_line, load_limit_up_list, get_target_stocks, setup_logger
from utils.config import DECODED_DIR, LIMIT_UP_FILE, DEFAULT_MAX_WORKERS, MARKETS

# 自訂資料目錄
CUSTOM_DATA_DIR = Path(r"C:\Users\user\Documents\_08_holdwin_data\_01_web\data")


def read_quote_file_fast(file_path: Path, target_stocks: Set[str], date_str: str) -> Dict[str, list]:
    """
    快速讀取並解析 Quote 檔案

    Args:
        file_path: Quote 檔案路徑
        target_stocks: 目標股票代碼集合
        date_str: 日期字串

    Returns:
        (股票資料字典, 統計資料)
    """
    stock_data = {stock: [] for stock in target_stocks}
    stats = {'trade': 0, 'depth': 0}

    # 使用較大的 buffer 提升 I/O 效能
    with open(file_path, 'r', encoding='utf-8', errors='ignore', buffering=1024*1024) as f:
        for line in f:
            # 快速過濾
            if len(line) < 10:
                continue

            line_type = line[:6]
            if line_type not in ('Trade,', 'Depth,'):
                continue

            # 提取股票代碼（優化：直接切片而非 split）
            try:
                stock_code = line.split(',', 2)[1].strip()
                if stock_code not in target_stocks:
                    continue
            except:
                continue

            # 解析資料
            if line_type == 'Trade,':
                parsed = parse_trade_line(line, date_str)
                if parsed:
                    stock_data[stock_code].append(parsed)
                    stats['trade'] += 1
            else:
                parsed = parse_depth_line(line, date_str)
                if parsed:
                    stock_data[stock_code].append(parsed)
                    stats['depth'] += 1

    return stock_data, stats


def process_quote_file(file_path: Path, target_stocks: Set[str], date_str: str,
                       output_dir: Path, logger, data_dir: Path = None) -> int:
    """處理單個 Quote 檔案"""
    logger.info(f"處理: {file_path.name}")

    stock_data, stats = read_quote_file_fast(file_path, target_stocks, date_str)

    if not stock_data:
        logger.warning("  無資料")
        return 0

    # 批次保存
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_count = 0

    for stock_code, records in stock_data.items():
        if not records:
            continue

        df = pd.DataFrame(records)
        if 'Datetime' in df.columns:
            df.sort_values('Datetime', inplace=True)

        output_path = output_dir / f"{stock_code}.parquet"
        df.to_parquet(output_path, index=False, compression='snappy')
        saved_count += 1

    logger.info(f"  Trade={stats['trade']}, Depth={stats['depth']}, 保存={saved_count}支")
    return saved_count


def process_date(date_str: str, limit_up_dict: Dict[str, Set[str]],
                data_dir: Path, output_base_dir: Path, logger) -> int:
    """處理單個日期的資料"""
    logger.info(f"{'='*60}\n處理日期: {date_str}\n{'='*60}")

    target_stocks = get_target_stocks(limit_up_dict, date_str)
    if not target_stocks:
        logger.info("  無目標股票")
        return 0

    logger.info(f"  目標股票: {len(target_stocks)}支")

    # 檢查是否已處理
    output_dir = output_base_dir / date_str
    if output_dir.exists():
        existing = {f.stem for f in output_dir.glob('*.parquet')}
        if target_stocks.issubset(existing):
            logger.info("  已完成，跳過")
            return 0

    total_saved = 0
    for market in MARKETS:
        quote_file = data_dir / f"{market}Quote.{date_str}"
        if quote_file.exists():
            total_saved += process_quote_file(quote_file, target_stocks, date_str, output_dir, logger)
        else:
            logger.warning(f"  未找到 {market}Quote.{date_str}")

    logger.info(f"  完成，共保存 {total_saved} 支")
    return total_saved


def process_specific_stocks(date_str: str, stock_codes: List[str], markets: List[str],
                           data_dir: Path, output_base_dir: Path, logger) -> int:
    """
    處理指定的股票代碼

    Args:
        date_str: 日期字串 (YYYYMMDD)
        stock_codes: 股票代碼列表
        markets: 市場列表 ['TSE', 'OTC']
        data_dir: 資料目錄
        output_base_dir: 輸出基礎目錄
        logger: 日誌記錄器

    Returns:
        保存的股票數量
    """
    logger.info(f"{'='*60}\n處理日期: {date_str}\n{'='*60}")

    target_stocks = set(stock_codes)
    logger.info(f"  目標股票: {len(target_stocks)}支 - {', '.join(sorted(target_stocks))}")

    # 準備輸出目錄
    output_dir = output_base_dir / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    total_saved = 0
    for market in markets:
        quote_file = data_dir / f"{market}Quote.{date_str}"
        if quote_file.exists():
            logger.info(f"\n處理市場: {market}")
            total_saved += process_quote_file(quote_file, target_stocks, date_str, output_dir, logger, data_dir)
        else:
            logger.warning(f"  未找到 {market}Quote.{date_str}")

    logger.info(f"\n完成，共保存 {total_saved} 支股票")
    return total_saved


def interactive_mode(logger):
    """互動模式：讓使用者輸入參數"""
    logger.info("="*80)
    logger.info("互動模式 - 指定股票解碼")
    logger.info("="*80)

    # 輸入日期
    date_str = input("\n請輸入日期 (YYYYMMDD，例如 20240101): ").strip()
    if not re.match(r'^\d{8}$', date_str):
        logger.error("日期格式錯誤！請使用 YYYYMMDD 格式")
        return

    # 輸入股票代碼
    stocks_input = input("請輸入股票代碼（多個股票用逗號分隔，例如 2330,2317,2454): ").strip()
    stock_codes = [s.strip() for s in stocks_input.split(',') if s.strip()]

    if not stock_codes:
        logger.error("未輸入股票代碼！")
        return

    # 選擇市場
    market_input = input("請選擇市場 (TSE/OTC/BOTH，預設 BOTH): ").strip().upper()
    if market_input in ['TSE', 'OTC']:
        markets = [market_input]
    else:
        markets = ['TSE', 'OTC']

    # 自訂輸出路徑
    output_input = input(f"輸出目錄（預設 {DECODED_DIR}，直接按 Enter 使用預設）: ").strip()
    output_dir = Path(output_input) if output_input else DECODED_DIR

    logger.info(f"\n資料來源: {CUSTOM_DATA_DIR}")
    logger.info(f"輸出目錄: {output_dir}")

    # 執行處理
    process_specific_stocks(date_str, stock_codes, markets, CUSTOM_DATA_DIR, output_dir, logger)


def batch_mode(logger):
    """批次模式：使用漲停清單處理"""
    logger.info("="*80)
    logger.info("批次模式 - 使用漲停清單")
    logger.info("="*80)

    # 檢查漲停清單
    if not LIMIT_UP_FILE.exists():
        logger.error(f"錯誤: 找不到漲停清單 {LIMIT_UP_FILE}")
        return

    # 載入漲停清單
    logger.info(f"\n載入漲停清單: {LIMIT_UP_FILE}")
    limit_up_dict = load_limit_up_list(LIMIT_UP_FILE)
    logger.info(f"共載入 {len(limit_up_dict)} 個日期")

    # 掃描 Quote 檔案
    all_dates = set()
    for market in MARKETS:
        for f in glob.glob(str(CUSTOM_DATA_DIR / f"{market}Quote.*")):
            match = re.search(r'(\d{8})$', Path(f).name)
            if match:
                all_dates.add(match.group(1))

    all_dates = sorted(all_dates)
    if not all_dates:
        logger.warning("未找到 Quote 檔案")
        return

    logger.info(f"\n找到 {len(all_dates)} 個日期: {all_dates[0]} ~ {all_dates[-1]}")

    # 過濾需要處理的日期
    dates_to_process = [d for d in all_dates if get_target_stocks(limit_up_dict, d)]
    logger.info(f"需處理: {len(dates_to_process)} 個日期")

    if not dates_to_process:
        logger.warning("無需處理的日期")
        return

    # 多線程處理
    logger.info(f"\n使用 {DEFAULT_MAX_WORKERS} 個線程並行處理\n")

    total_saved = 0
    completed = {'count': 0}
    lock = threading.Lock()

    def process_with_progress(date_str):
        try:
            saved = process_date(date_str, limit_up_dict, CUSTOM_DATA_DIR, DECODED_DIR, logger)
            with lock:
                completed['count'] += 1
                logger.info(f"\n[進度: {completed['count']}/{len(dates_to_process)}]")
            return saved
        except Exception as e:
            logger.error(f"\n處理 {date_str} 錯誤: {e}")
            return 0

    with ThreadPoolExecutor(max_workers=DEFAULT_MAX_WORKERS) as executor:
        futures = [executor.submit(process_with_progress, date) for date in dates_to_process]
        for future in as_completed(futures):
            total_saved += future.result()

    logger.info("\n" + "="*80)
    logger.info("批次處理完成！")
    logger.info(f"處理日期: {len(dates_to_process)}")
    logger.info(f"保存檔案: {total_saved}")
    logger.info(f"輸出目錄: {DECODED_DIR}")
    logger.info("="*80)


def process_single_date(date_str: str, markets: List[str], output_base_dir: Path, logger) -> int:
    """
    處理單一日期的所有漲停股票

    Args:
        date_str: 日期字串 (YYYYMMDD)
        markets: 市場列表 ['TSE', 'OTC']
        output_base_dir: 輸出基礎目錄
        logger: 日誌記錄器

    Returns:
        保存的股票數量
    """
    logger.info(f"{'='*60}\n處理日期: {date_str}\n{'='*60}")

    # 載入漲停清單
    if not LIMIT_UP_FILE.exists():
        logger.error(f"找不到漲停清單: {LIMIT_UP_FILE}")
        return 0

    limit_up_dict = load_limit_up_list(LIMIT_UP_FILE)
    target_stocks = get_target_stocks(limit_up_dict, date_str)

    if not target_stocks:
        logger.warning(f"日期 {date_str} 沒有漲停股票記錄")
        return 0

    logger.info(f"目標股票: {len(target_stocks)} 支")

    # 準備輸出目錄
    output_dir = output_base_dir / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    total_saved = 0
    for market in markets:
        quote_file = CUSTOM_DATA_DIR / f"{market}Quote.{date_str}"
        if quote_file.exists():
            logger.info(f"\n處理市場: {market}")
            total_saved += process_quote_file(quote_file, target_stocks, date_str, output_dir, logger)
        else:
            logger.warning(f"未找到 {market}Quote.{date_str}")

    logger.info(f"\n完成，共保存 {total_saved} 支股票")
    return total_saved


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description='Quote 檔案解碼工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  批次模式（使用漲停清單處理所有日期）:
    python decode.py

  單日模式（處理特定日期的漲停股票）:
    python decode.py --date 20240101
    python decode.py -d 20240101 -m TSE

  指定模式（處理特定日期的特定股票）:
    python decode.py --date 20240101 --stocks 2330,2317 --market TSE
    python decode.py -d 20240101 -s 2330,2317,2454 -m BOTH

  互動模式:
    python decode.py --interactive
    python decode.py -i
        """
    )

    parser.add_argument('-d', '--date', help='指定日期 (YYYYMMDD)')
    parser.add_argument('-s', '--stocks', help='股票代碼（多個用逗號分隔，例如 2330,2317）')
    parser.add_argument('-m', '--market', choices=['TSE', 'OTC', 'BOTH'], default='BOTH',
                       help='指定市場 (預設: BOTH)')
    parser.add_argument('-o', '--output', help=f'輸出目錄 (預設: {DECODED_DIR})')
    parser.add_argument('-i', '--interactive', action='store_true', help='互動模式')

    args = parser.parse_args()
    logger = setup_logger('decode')

    # 互動模式
    if args.interactive:
        interactive_mode(logger)
        return

    # 指定模式：日期 + 股票
    if args.date and args.stocks:
        logger.info("="*80)
        logger.info("指定模式 - 解碼特定股票")
        logger.info("="*80)

        stock_codes = [s.strip() for s in args.stocks.split(',') if s.strip()]
        markets = ['TSE', 'OTC'] if args.market == 'BOTH' else [args.market]
        output_dir = Path(args.output) if args.output else DECODED_DIR

        logger.info(f"\n資料來源: {CUSTOM_DATA_DIR}")
        logger.info(f"輸出目錄: {output_dir}")

        process_specific_stocks(args.date, stock_codes, markets, CUSTOM_DATA_DIR, output_dir, logger)
        return

    # 單日模式：只指定日期，處理該日漲停股票
    if args.date and not args.stocks:
        logger.info("="*80)
        logger.info("單日模式 - 解碼特定日期的漲停股票")
        logger.info("="*80)

        markets = ['TSE', 'OTC'] if args.market == 'BOTH' else [args.market]
        output_dir = Path(args.output) if args.output else DECODED_DIR

        logger.info(f"\n資料來源: {CUSTOM_DATA_DIR}")
        logger.info(f"輸出目錄: {output_dir}")

        process_single_date(args.date, markets, output_dir, logger)
        return

    # 批次模式
    if not args.date and not args.stocks:
        batch_mode(logger)
        return

    # 參數不完整
    logger.error("參數錯誤！使用 --help 查看使用說明")
    logger.error("請使用 --date 指定日期，或使用 --interactive 進入互動模式")


if __name__ == "__main__":
    main()
