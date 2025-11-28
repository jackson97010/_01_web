#!/usr/bin/env python3
"""
單一股票資料查詢工具（優化版）
從原始 Quote 檔案中提取指定股票的資料

使用範例:
    python query_stock.py 20251031 TSE 2330 --output console
    python query_stock.py 20251125 OTC 8042 --output parquet
    python query_stock.py 20251125 TSE 2330 --output json
"""
import pandas as pd
import argparse
import json
from pathlib import Path

from utils import parse_trade_line, parse_depth_line, setup_logger
from utils.config import DATA_DIR, QUERY_RESULTS_DIR, MARKETS


def main():
    """主程式"""
    parser = argparse.ArgumentParser(description="從原始 Quote 檔案中查詢單一股票的資料")
    parser.add_argument("date", type=str, help="查詢日期 (格式: YYYYMMDD)")
    parser.add_argument("market", type=str, choices=MARKETS, help="市場別 (OTC 或 TSE)")
    parser.add_argument("stock_code", type=str, help="股票代號")
    parser.add_argument(
        "--output",
        type=str,
        choices=['console', 'parquet', 'json'],
        default='console',
        help="輸出格式 (預設: console)"
    )
    args = parser.parse_args()

    # 設定日誌
    logger = setup_logger('query_stock')

    logger.info(f"查詢條件: 日期={args.date}, 市場={args.market}, 股票={args.stock_code}, 輸出={args.output}")

    # 確保輸出目錄存在
    QUERY_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 尋找原始檔案
    quote_file_path = DATA_DIR / f"{args.market}Quote.{args.date}"
    if not quote_file_path.exists():
        logger.error(f"\n錯誤: 找不到原始資料檔案: {quote_file_path}")
        return

    logger.info(f"正在讀取檔案: {quote_file_path}")

    # 讀取並解析資料
    records = []
    try:
        with open(quote_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # 快速過濾，只處理包含目標股票代號的行
                if f",{args.stock_code}," not in line and f",{args.stock_code} " not in line:
                    continue

                parsed = None
                if line.startswith('Trade,'):
                    parsed = parse_trade_line(line, args.date)
                elif line.startswith('Depth,'):
                    parsed = parse_depth_line(line, args.date)

                if parsed and parsed['StockCode'] == args.stock_code:
                    records.append(parsed)
    except Exception as e:
        logger.error(f"讀取或解析檔案時發生錯誤: {e}")
        return

    if not records:
        logger.warning(f"\n查詢完成，但在檔案中找不到股票 {args.stock_code} 的任何資料。")
        return

    # 轉換為 DataFrame
    df = pd.DataFrame(records)
    if 'Datetime' in df.columns:
        df = df.sort_values('Datetime').reset_index(drop=True)

    trade_count = len(df[df['Type']=='Trade'])
    depth_count = len(df[df['Type']=='Depth'])
    logger.info(f"\n查詢成功！共找到 {len(df)} 筆記錄 (Trade: {trade_count}, Depth: {depth_count}).")

    # 根據參數輸出結果
    if args.output == 'console':
        print("\n" + "=" * 80)
        print("資料預覽 (前 10 筆)")
        print("=" * 80)
        print(df.head(10).to_string())
        print("\n" + "=" * 80)
        print("資料預覽 (後 10 筆)")
        print("=" * 80)
        print(df.tail(10).to_string())

    elif args.output == 'parquet':
        output_path = QUERY_RESULTS_DIR / f"{args.date}_{args.stock_code}.parquet"
        df.to_parquet(output_path, index=False)
        logger.info(f"\n資料已儲存至: {output_path}")

    elif args.output == 'json':
        output_path = QUERY_RESULTS_DIR / f"{args.date}_{args.stock_code}.json"
        # 將 Datetime 轉換為字串以利 JSON 序列化
        df['Datetime'] = df['Datetime'].astype(str)
        df.to_json(output_path, orient='records', indent=2, force_ascii=False)
        logger.info(f"\n資料已儲存至: {output_path}")


if __name__ == "__main__":
    main()
