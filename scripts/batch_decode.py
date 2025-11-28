#!/usr/bin/env python3
"""
OTC/TSE Quote 批次解碼程式（優化版）
將原始 Quote 檔案解碼並儲存為 Parquet 格式

特色：
- 模組化設計，使用共用工具庫
- 多線程並行處理
- 自動跳過已處理檔案
- 詳細的進度顯示和日誌
"""
import pandas as pd
import os
import re
import glob
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Set, Dict

# 導入共用工具
from utils import load_limit_up_list, get_target_stocks, read_quote_file, setup_logger
from utils.config import DATA_DIR, DECODED_DIR, LIMIT_UP_FILE, DEFAULT_MAX_WORKERS, MARKETS


def process_quote_file(file_path: Path, target_stocks: Set[str], date_str: str, output_dir: Path, logger) -> int:
    """
    處理單個 Quote 檔案

    Args:
        file_path: Quote 檔案路徑
        target_stocks: 目標股票代碼集合
        date_str: 日期字串
        output_dir: 輸出目錄
        logger: 日誌記錄器

    Returns:
        成功處理的股票數量
    """
    logger.info(f"處理: {file_path.name}")

    # 讀取並解析資料
    stock_data, stats = read_quote_file(file_path, target_stocks, date_str)

    if not stock_data:
        logger.warning(f"  無法讀取資料")
        return 0

    # 保存資料
    saved_count = 0
    output_dir.mkdir(parents=True, exist_ok=True)

    for stock_code, records in stock_data.items():
        if not records:
            continue

        # 轉換為 DataFrame
        df = pd.DataFrame(records)

        # 按時間排序
        if 'Datetime' in df.columns:
            df = df.sort_values('Datetime').reset_index(drop=True)

        # 儲存
        output_path = output_dir / f"{stock_code}.parquet"
        df.to_parquet(output_path, index=False)
        saved_count += 1

    logger.info(f"  Trade={stats['trade']}, Depth={stats['depth']}, 已保存={saved_count}支")
    return saved_count


def process_date(date_str: str, limit_up_dict: Dict[str, Set[str]], data_dir: Path, output_base_dir: Path, logger) -> int:
    """
    處理單個日期的 OTC 和 TSE 檔案

    Args:
        date_str: 日期字串 (YYYYMMDD)
        limit_up_dict: 漲停清單字典
        data_dir: 資料目錄
        output_base_dir: 輸出基礎目錄
        logger: 日誌記錄器

    Returns:
        成功處理的股票數量
    """
    logger.info(f"{'='*60}")
    logger.info(f"處理日期: {date_str}")
    logger.info(f"{'='*60}")

    # 取得目標股票
    target_stocks = get_target_stocks(limit_up_dict, date_str)

    if not target_stocks:
        logger.info("  無目標股票，跳過")
        return 0

    logger.info(f"  目標股票: {len(target_stocks)}支")

    # 檢查是否已處理完成
    output_dir = output_base_dir / date_str
    if output_dir.exists():
        existing_files = set(os.listdir(output_dir))
        expected_files = {f"{stock}.parquet" for stock in target_stocks}
        if expected_files.issubset(existing_files):
            logger.info("  所有檔案已存在，跳過")
            return 0

    total_saved = 0

    # 處理 OTC 和 TSE
    for market in MARKETS:
        quote_file = data_dir / f"{market}Quote.{date_str}"

        if quote_file.exists():
            saved = process_quote_file(quote_file, target_stocks, date_str, output_dir, logger)
            total_saved += saved
        else:
            logger.warning(f"  未找到 {market}Quote.{date_str}")

    logger.info(f"  日期 {date_str} 完成，共保存 {total_saved} 支股票")
    return total_saved


def main():
    """主程式"""
    # 設定日誌
    logger = setup_logger('batch_decode')

    logger.info("=" * 80)
    logger.info("OTC/TSE Quote 批次解碼程式（優化版）")
    logger.info("=" * 80)

    # 檢查漲停清單檔案
    if not LIMIT_UP_FILE.exists():
        logger.error(f"錯誤: 找不到漲停清單檔案 {LIMIT_UP_FILE}")
        return

    # 載入漲停清單
    logger.info(f"\n載入漲停清單: {LIMIT_UP_FILE}")
    limit_up_dict = load_limit_up_list(LIMIT_UP_FILE)
    logger.info(f"共載入 {len(limit_up_dict)} 個日期的漲停資料")

    # 掃描所有 Quote 檔案
    all_dates = set()

    for market in MARKETS:
        pattern = str(DATA_DIR / f"{market}Quote.*")
        files = glob.glob(pattern)
        for f in files:
            match = re.search(r'(\d{8})$', os.path.basename(f))
            if match:
                all_dates.add(match.group(1))

    all_dates = sorted(all_dates)

    if not all_dates:
        logger.warning("沒有找到 Quote 檔案")
        return

    logger.info(f"\n找到 {len(all_dates)} 個日期: {all_dates[0]} ~ {all_dates[-1]}")

    # 過濾出有漲停股票的日期
    dates_to_process = []
    for date_str in all_dates:
        target_stocks = get_target_stocks(limit_up_dict, date_str)
        if target_stocks:
            dates_to_process.append(date_str)

    logger.info(f"需要處理的日期: {len(dates_to_process)} 個")

    if not dates_to_process:
        logger.warning("沒有需要處理的日期")
        return

    # 多線程處理
    max_workers = DEFAULT_MAX_WORKERS
    logger.info(f"\n將使用 {max_workers} 個線程並行處理")
    logger.info("\n開始處理...")

    total_files_saved = 0
    completed = {'count': 0}
    lock = threading.Lock()

    def process_with_progress(date_str):
        """帶進度顯示的處理函數"""
        try:
            saved = process_date(date_str, limit_up_dict, DATA_DIR, DECODED_DIR, logger)
            with lock:
                completed['count'] += 1
                logger.info(f"\n[進度: {completed['count']}/{len(dates_to_process)}]")
            return saved
        except Exception as e:
            logger.error(f"\n處理 {date_str} 時發生錯誤: {e}")
            return 0

    # 執行處理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_with_progress, date) for date in dates_to_process]

        for future in as_completed(futures):
            try:
                saved = future.result()
                total_files_saved += saved
            except Exception as e:
                logger.error(f"執行錯誤: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("批次處理完成！")
    logger.info(f"處理日期數: {len(dates_to_process)}")
    logger.info(f"保存檔案數: {total_files_saved}")
    logger.info(f"輸出目錄: {DECODED_DIR}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
