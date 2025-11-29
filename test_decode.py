"""
測試 Quote 檔案解碼
"""
import pandas as pd

def parse_trade_line(line):
    """解析 Trade 行"""
    fields = line.strip().split(',')
    if len(fields) < 7:
        return None

    return {
        'Type': fields[0],
        'StockCode': fields[1].strip(),
        'Timestamp': fields[2].strip(),
        'Flag': fields[3],
        'Price_Raw': fields[4],
        'Price': int(fields[4]) / 10000,
        'Volume': fields[5],
        'TotalVolume': fields[6]
    }

def parse_depth_line(line):
    """解析 Depth 行"""
    fields = line.strip().split(',')
    if len(fields) < 4:
        return None

    result = {
        'Type': fields[0],
        'StockCode': fields[1].strip(),
        'Timestamp': fields[2].strip(),
    }

    # 找到 BID 和 ASK 的位置
    bid_idx = -1
    ask_idx = -1

    for i, field in enumerate(fields):
        if 'BID:' in field:
            bid_idx = i
            result['BID_Count'] = field.split(':')[1]
        elif 'ASK:' in field:
            ask_idx = i
            result['ASK_Count'] = field.split(':')[1]

    if bid_idx == -1 or ask_idx == -1:
        return None

    # 解析買盤檔位
    bid_fields = fields[bid_idx+1:ask_idx]
    result['BID_Data'] = []
    for bf in bid_fields:
        if '*' in bf:
            price_str, vol_str = bf.split('*')
            price = int(price_str) / 10000
            result['BID_Data'].append(f"{price}*{vol_str}")

    # 解析賣盤檔位
    ask_fields = fields[ask_idx+1:-1] if len(fields) > ask_idx+1 else []
    result['ASK_Data'] = []
    for af in ask_fields:
        if '*' in af:
            price_str, vol_str = af.split('*')
            price = int(price_str) / 10000
            result['ASK_Data'].append(f"{price}*{vol_str}")

    return result

# 測試解析
test_file = r'C:\Users\User\Documents\_web\_01_web\data\OTCQuote.20251031'

print("=" * 80)
print("測試解碼 OTCQuote.20251031")
print("=" * 80)

# 目標股票（2025-10-30 + 2025-10-31 的漲停股票）
target_stocks_1030 = ['2485', '2612', '2615', '3006', '3047', '3062', '3234', '3543', '6152', '6163']
target_stocks_1031 = ['1503', '1514', '1519', '2368', '3105', '3711', '4991', '5381', '5439', '8047', '8183']
target_stocks = set(target_stocks_1030 + target_stocks_1031)

print(f"\n目標股票清單 ({len(target_stocks)}支):")
print(sorted(target_stocks))

# 讀取並解析
found_stocks = set()
trade_count = 0
depth_count = 0

print("\n開始解析前100行資料...")
print("-" * 80)

with open(test_file, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i >= 100:  # 只看前100行
            break

        line = line.strip()

        if line.startswith('Trade,'):
            parsed = parse_trade_line(line)
            if parsed and parsed['StockCode'] in target_stocks:
                print(f"\n[Trade] 股票: {parsed['StockCode']}")
                print(f"  原始價格: {parsed['Price_Raw']} -> 解碼價格: {parsed['Price']}")
                print(f"  時間戳: {parsed['Timestamp']}")
                print(f"  試撮旗標: {parsed['Flag']} ({'試算' if parsed['Flag'] == '1' else '一般'})")
                print(f"  成交量: {parsed['Volume']}, 總量: {parsed['TotalVolume']}")
                found_stocks.add(parsed['StockCode'])
                trade_count += 1

        elif line.startswith('Depth,'):
            parsed = parse_depth_line(line)
            if parsed and parsed['StockCode'] in target_stocks:
                print(f"\n[Depth] 股票: {parsed['StockCode']}")
                print(f"  時間戳: {parsed['Timestamp']}")
                print(f"  買盤檔數: {parsed['BID_Count']}, 前3檔: {parsed['BID_Data'][:3]}")
                print(f"  賣盤檔數: {parsed['ASK_Count']}, 前3檔: {parsed['ASK_Data'][:3]}")
                found_stocks.add(parsed['StockCode'])
                depth_count += 1

print("\n" + "=" * 80)
print(f"解析統計:")
print(f"  找到目標股票: {len(found_stocks)}支 -> {sorted(found_stocks)}")
print(f"  Trade 記錄: {trade_count} 筆")
print(f"  Depth 記錄: {depth_count} 筆")
print("=" * 80)

# 檢查整個檔案中的目標股票
print("\n掃描整個檔案...")
all_found_stocks = set()
all_trade = 0
all_depth = 0

with open(test_file, 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('Trade,') or line.startswith('Depth,'):
            fields = line.strip().split(',')
            if len(fields) >= 2:
                stock_code = fields[1].strip()
                if stock_code in target_stocks:
                    all_found_stocks.add(stock_code)
                    if line.startswith('Trade,'):
                        all_trade += 1
                    else:
                        all_depth += 1

print(f"\n整個檔案中找到的目標股票: {len(all_found_stocks)}支")
print(f"  股票清單: {sorted(all_found_stocks)}")
print(f"  Trade 總數: {all_trade} 筆")
print(f"  Depth 總數: {all_depth} 筆")
print(f"\n未找到的股票: {sorted(target_stocks - all_found_stocks)}")
