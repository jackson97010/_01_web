#!/usr/bin/env python3
"""
Parquet 轉 JSON 資料轉換程式（優化版）
將解碼後的 Parquet 檔案轉換為前端所需的 JSON 格式

特色：
- 模組化設計
- 多進程並行處理
- 自動跳過已轉換檔案
- 完整的資料處理（VWAP、內外盤判斷、統計資料）

使用範例:
1. 轉換所有日期:
   python data_convert.py

2. 指定單一日期:
   python data_convert.py --date 20251219

3. 指定日期範圍:
   python data_convert.py --start 20251201 --end 20251219

4. 強制重新轉換（忽略已存在的檔案）:
   python data_convert.py --date 20251219 --force
"""
import pandas as pd
import os
import json
import argparse
import glob
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


def determine_tick_type(trade_price: float, best_bid: Optional[float], best_ask: Optional[float]) -> int:
    """
    使用 Double Buffer 方法判斷內外盤（tick_type）

    Args:
        trade_price: 成交價
        best_bid: 最佳買價
        best_ask: 最佳賣價

    Returns:
        1: 外盤（買）- price >= best_ask
        2: 內盤（賣）- price <= best_bid
        0: 未判定
    """
    if trade_price is None or trade_price <= 0:
        return 0
    if best_ask is not None and trade_price >= best_ask:
        return 1  # 外盤
    if best_bid is not None and trade_price <= best_bid:
        return 2  # 內盤
    return 0  # 未判定（價格在 bid/ask 之間）


def tick_type_to_label(tick_type: int) -> str:
    """將 tick_type 轉換為中文標籤"""
    if tick_type == 1:
        return '外盤'
    elif tick_type == 2:
        return '內盤'
    return '–'


def filter_trading_hours(df: pd.DataFrame) -> pd.DataFrame:
    """過濾出 09:00 以後的交易資料（排除試撮時段）"""
    if df.empty:
        return df
    # 取得時間的 hour，只保留 9 點以後的資料
    return df[df['Datetime'].dt.hour >= 9].copy()


def prepare_chart_data(trade_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """準備圖表資料（只計算 09:00 以後的資料）"""
    if trade_df.empty:
        return None

    # 過濾 09:00 以後的資料用於 VWAP 計算
    trade_df = trade_df.sort_values('Datetime').reset_index(drop=True)
    trade_df_filtered = filter_trading_hours(trade_df)

    timestamps = [str(ts) for ts in trade_df['Datetime']]
    prices = [float(p) if pd.notna(p) else 0.0 for p in trade_df['Price']]
    volumes = [int(v) if pd.notna(v) else 0 for v in trade_df['Volume']]

    # 計算累計成交量（使用過濾後的資料）
    filtered_prices = [float(p) if pd.notna(p) else 0.0 for p in trade_df_filtered['Price']] if not trade_df_filtered.empty else []
    filtered_volumes = [int(v) if pd.notna(v) else 0 for v in trade_df_filtered['Volume']] if not trade_df_filtered.empty else []

    # 計算累計成交量
    total_volumes = []
    cumsum = 0
    for v in volumes:
        cumsum += v
        total_volumes.append(cumsum)

    # 計算 VWAP（只用 09:00 以後的資料）
    vwap_filtered = calculate_vwap(filtered_prices, filtered_volumes) if filtered_prices else []

    # 將 VWAP 對應回所有時間點（09:00 前的用 0 或第一個有效值）
    vwap = []
    vwap_idx = 0
    for ts in trade_df['Datetime']:
        if ts.hour >= 9 and vwap_idx < len(vwap_filtered):
            vwap.append(vwap_filtered[vwap_idx])
            vwap_idx += 1
        else:
            # 09:00 前用 0 或用第一個有效 VWAP
            vwap.append(vwap_filtered[0] if vwap_filtered else 0.0)

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
    """準備五檔歷史資料 - 優化版"""
    if depth_df.empty:
        return []

    depth_df = depth_df.sort_values('Datetime').reset_index(drop=True)

    # 預先取出所有欄位的值（避免重複 .get()）
    timestamps = depth_df['Datetime'].astype(str).tolist()

    # 預先取出所有五檔價量
    bid_prices = [depth_df.get(f'Bid{i}_Price') for i in range(1, 6)]
    bid_volumes = [depth_df.get(f'Bid{i}_Volume') for i in range(1, 6)]
    ask_prices = [depth_df.get(f'Ask{i}_Price') for i in range(1, 6)]
    ask_volumes = [depth_df.get(f'Ask{i}_Volume') for i in range(1, 6)]

    history = []
    for idx in range(len(depth_df)):
        bids = []
        asks = []

        for i in range(5):
            # 買盤
            if bid_prices[i] is not None:
                bp = bid_prices[i].iloc[idx]
                bv = bid_volumes[i].iloc[idx] if bid_volumes[i] is not None else None
                if pd.notna(bp) and pd.notna(bv):
                    bids.append({'price': float(bp), 'volume': int(bv)})

            # 賣盤
            if ask_prices[i] is not None:
                ap = ask_prices[i].iloc[idx]
                av = ask_volumes[i].iloc[idx] if ask_volumes[i] is not None else None
                if pd.notna(ap) and pd.notna(av):
                    asks.append({'price': float(ap), 'volume': int(av)})

        history.append({
            'timestamp': timestamps[idx],
            'bids': bids,
            'asks': asks
        })

    return history


def prepare_trade_details_double_buffer(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    準備成交明細（含內外盤判斷）- 使用 Double Buffer 方法

    Double Buffer 邏輯：
    - latest_depth: 最新的 depth
    - second_latest_depth: 第二新的 depth
    - Trade 判定時，如果 Trade 和 latest_depth 同 timestamp，用 second_latest_depth
    - 否則用 latest_depth
    """
    if df.empty:
        return []

    # 按時間排序（正序處理）
    df_sorted = df.sort_values('Datetime').reset_index(drop=True)

    # Double Buffer 狀態
    latest_depth = None  # {'bid': float, 'ask': float, 'timestamp': Timestamp}
    second_latest_depth = None

    # 儲存每筆 Trade 的結果
    trade_results = []

    for _, row in df_sorted.iterrows():
        row_type = row.get('Type', '')
        timestamp = row['Datetime']

        if row_type == 'Depth':
            # 更新 depth state: second_latest = latest, latest = new
            bid1 = row.get('Bid1_Price')
            ask1 = row.get('Ask1_Price')

            if pd.notna(bid1) and pd.notna(ask1) and bid1 > 0 and ask1 > 0:
                second_latest_depth = latest_depth
                latest_depth = {
                    'bid': float(bid1),
                    'ask': float(ask1),
                    'timestamp': timestamp
                }

        elif row_type == 'Trade':
            price = row.get('Price', 0)
            volume = row.get('Volume', 0)
            flag = row.get('Flag', 0)

            # 使用 Double Buffer 邏輯取得 depth
            depth_to_use = None
            if latest_depth is not None:
                # 如果 Trade 和 latest_depth 同 timestamp，用 second_latest_depth
                if latest_depth['timestamp'] == timestamp:
                    depth_to_use = second_latest_depth if second_latest_depth else latest_depth
                else:
                    depth_to_use = latest_depth

            # 計算 tick_type
            if depth_to_use and pd.notna(price) and price > 0 and pd.notna(volume) and volume > 0:
                tick_type = determine_tick_type(
                    float(price),
                    depth_to_use['bid'],
                    depth_to_use['ask']
                )
            else:
                tick_type = 0

            trade_results.append({
                'time': str(timestamp) if pd.notna(timestamp) else '',
                'price': float(price) if pd.notna(price) else 0.0,
                'volume': int(volume) if pd.notna(volume) else 0,
                'inner_outer': tick_type_to_label(tick_type),
                'tick_type': tick_type,
                'flag': int(flag) if pd.notna(flag) else 0
            })

    # 按時間倒序排列（最新的在前）
    trade_results.reverse()

    return trade_results


def prepare_trade_details(trade_df: pd.DataFrame, depth_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """準備成交明細 - 包裝函數，合併 Trade 和 Depth 後使用 Double Buffer"""
    if trade_df.empty:
        return []

    # 合併 Trade 和 Depth，按時間排序
    combined = pd.concat([trade_df, depth_df], ignore_index=True)
    return prepare_trade_details_double_buffer(combined)


def calculate_statistics(trade_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """計算統計資料（只計算 09:00 以後的資料）"""
    if trade_df.empty:
        return None

    trade_df = trade_df.sort_values('Datetime').reset_index(drop=True)

    # 過濾 09:00 以後的資料
    trade_df_filtered = filter_trading_hours(trade_df)

    if trade_df_filtered.empty:
        return None

    valid_prices = trade_df_filtered['Price'].dropna()
    valid_volumes = trade_df_filtered['Volume'].dropna()

    if valid_prices.empty:
        return None

    open_price = float(valid_prices.iloc[0])
    current_price = float(valid_prices.iloc[-1])
    high_price = float(valid_prices.max())
    low_price = float(valid_prices.min())

    # 計算平均成交價（成交量加權）
    valid_df = trade_df_filtered[trade_df_filtered['Price'].notna() & trade_df_filtered['Volume'].notna()]
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
        args: (parquet_file_path, output_base_dir, force)

    Returns:
        處理結果訊息
    """
    parquet_file, output_base_dir, force = args

    try:
        # 解析路徑
        parquet_path = Path(parquet_file)
        date_str = parquet_path.parent.name
        stock_code = parquet_path.stem

        # 檢查輸出檔案是否已存在
        output_dir = output_base_dir / date_str
        output_file = output_dir / f"{stock_code}.json"

        if not force and output_file.exists():
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
    # 解析命令列參數
    parser = argparse.ArgumentParser(description="將 Parquet 檔案轉換為前端 JSON 格式")
    parser.add_argument("--date", type=str, help="指定單一日期 (格式: YYYYMMDD)")
    parser.add_argument("--start", type=str, help="起始日期 (格式: YYYYMMDD)")
    parser.add_argument("--end", type=str, help="結束日期 (格式: YYYYMMDD)")
    parser.add_argument("--force", action="store_true", help="強制重新轉換（忽略已存在的檔案）")
    args = parser.parse_args()

    logger = setup_logger('data_convert')

    logger.info("=" * 80)
    logger.info("Parquet → JSON 資料轉換程式（優化版）")
    logger.info("=" * 80)

    if not DECODED_DIR.exists():
        logger.error(f"錯誤: 找不到解碼目錄 {DECODED_DIR}")
        logger.info("請先執行 batch_decode.py")
        return

    # 取得所有日期目錄
    date_dirs = sorted([d.name for d in DECODED_DIR.iterdir() if d.is_dir() and d.name.isdigit()])

    if not date_dirs:
        logger.warning("沒有找到任何日期目錄")
        return

    # 根據參數過濾日期
    if args.date:
        if args.date in date_dirs:
            date_dirs = [args.date]
        else:
            logger.error(f"錯誤: 找不到日期 {args.date} 的資料")
            logger.info(f"可用日期: {', '.join(date_dirs[:5])}..." if len(date_dirs) > 5 else f"可用日期: {', '.join(date_dirs)}")
            return
    elif args.start or args.end:
        start_date = args.start or date_dirs[0]
        end_date = args.end or date_dirs[-1]
        date_dirs = [d for d in date_dirs if start_date <= d <= end_date]
        if not date_dirs:
            logger.error(f"錯誤: 在 {start_date} ~ {end_date} 範圍內找不到資料")
            return

    logger.info(f"處理日期: {date_dirs[0]} ~ {date_dirs[-1]} (共 {len(date_dirs)} 天)")
    if args.force:
        logger.info("模式: 強制重新轉換")

    # 掃描指定日期的 Parquet 檔案
    parquet_files = []
    for date_str in date_dirs:
        pattern = str(DECODED_DIR / date_str / '*.parquet')
        parquet_files.extend(glob.glob(pattern))

    logger.info(f"找到 {len(parquet_files)} 個 Parquet 檔案")

    if not parquet_files:
        logger.warning("沒有找到任何 Parquet 檔案")
        return

    # 準備參數
    args_list = [(f, OUTPUT_DIR, args.force) for f in parquet_files]

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
