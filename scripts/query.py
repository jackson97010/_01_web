#!/usr/bin/env python3
"""
單一股票資料查詢工具
從原始 Quote 檔案快速提取指定股票的資料

使用範例:
    python query.py 20251031 TSE 2330 --output console
    python query.py 20251125 OTC 8042 --output parquet
    python query.py 20251125 TSE 2330 --output json
"""
import pandas as pd
import argparse
import json

from utils import parse_trade_line, parse_depth_line, setup_logger
from utils.config import DATA_DIR, QUERY_RESULTS_DIR, MARKETS


def main():
    """主程式"""
    parser = argparse.ArgumentParser(description="從原始 Quote 檔案查詢單一股票資料")
    parser.add_argument("date", help="日期 (YYYYMMDD)")
    parser.add_argument("market", choices=MARKETS, help="市場 (OTC/TSE)")
    parser.add_argument("stock_code", help="股票代號")
    parser.add_argument("--output", choices=['console', 'parquet', 'json'],
                       default='console', help="輸出格式 (預設: console)")
    args = parser.parse_args()

    logger = setup_logger('query')
    logger.info(f"查詢: 日期={args.date}, 市場={args.market}, 股票={args.stock_code}, 輸出={args.output}")

    # 確保輸出目錄存在
    QUERY_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 尋找檔案
    quote_file = DATA_DIR / f"{args.market}Quote.{args.date}"
    if not quote_file.exists():
        logger.error(f"錯誤: 找不到檔案 {quote_file}")
        return

    logger.info(f"讀取: {quote_file}")

    # 快速讀取並解析
    records = []
    stock_pattern = f",{args.stock_code},"

    with open(quote_file, 'r', encoding='utf-8', errors='ignore', buffering=1024*1024) as f:
        for line in f:
            # 快速過濾
            if stock_pattern not in line and f",{args.stock_code} " not in line:
                continue

            parsed = None
            if line.startswith('Trade,'):
                parsed = parse_trade_line(line, args.date)
            elif line.startswith('Depth,'):
                parsed = parse_depth_line(line, args.date)

            if parsed and parsed['StockCode'] == args.stock_code:
                records.append(parsed)

    if not records:
        logger.warning(f"未找到股票 {args.stock_code} 的資料")
        return

    # 轉換為 DataFrame
    df = pd.DataFrame(records)
    if 'Datetime' in df.columns:
        df.sort_values('Datetime', inplace=True)
        df.reset_index(drop=True, inplace=True)

    trade_count = (df['Type'] == 'Trade').sum()
    depth_count = (df['Type'] == 'Depth').sum()
    logger.info(f"成功！共 {len(df)} 筆 (Trade: {trade_count}, Depth: {depth_count})")

    # 輸出
    if args.output == 'console':
        print("\n" + "="*80)
        print("資料預覽 (前 10 筆)")
        print("="*80)
        print(df.head(10).to_string())
        print("\n" + "="*80)
        print("資料預覽 (後 10 筆)")
        print("="*80)
        print(df.tail(10).to_string())

    elif args.output == 'parquet':
        output_path = QUERY_RESULTS_DIR / f"{args.date}_{args.stock_code}.parquet"
        df.to_parquet(output_path, index=False)
        logger.info(f"已儲存: {output_path}")

    elif args.output == 'json':
        output_path = QUERY_RESULTS_DIR / f"{args.date}_{args.stock_code}.json"
        df['Datetime'] = df['Datetime'].astype(str)
        df.to_json(output_path, orient='records', indent=2, force_ascii=False)
        logger.info(f"已儲存: {output_path}")


if __name__ == "__main__":
    main()
