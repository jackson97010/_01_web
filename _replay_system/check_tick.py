import json
import sys

# 檢查特定時間點的數據
file_path = r"C:\Users\User\Documents\HFT\_replay_system\3060_1219.json"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"總共 {len(data)} 筆數據\n")

    # 查找 09:13:00 附近的數據
    target_time = "09:13:0"  # 部分匹配
    found_trades = []
    found_depths = []

    for item in data:
        if target_time in str(item.get('Datetime', '')):
            if item['Type'] == 'Trade':
                found_trades.append(item)
            elif item['Type'] == 'Depth':
                found_depths.append(item)

    print(f"找到 09:13:00 附近的成交數據 {len(found_trades)} 筆")
    print(f"找到 09:13:00 附近的五檔數據 {len(found_depths)} 筆\n")

    # 顯示成交數據
    print("成交數據：")
    for trade in found_trades[:10]:  # 只顯示前10筆
        print(f"  時間: {trade['Datetime']}")
        print(f"  價格: {trade.get('Price')}")
        print(f"  量: {trade.get('Volume')}")
        print(f"  BS_Flag: {trade.get('BS_Flag')}")
        print(f"  Timestamp: {trade.get('Timestamp')}")
        print("  ---")

    # 顯示最接近的五檔數據
    print("\n五檔數據（前3筆）：")
    for depth in found_depths[:3]:
        print(f"  時間: {depth['Datetime']}")
        print(f"  買一: {depth.get('Bid1_Price')} @ {depth.get('Bid1_Volume')}")
        print(f"  賣一: {depth.get('Ask1_Price')} @ {depth.get('Ask1_Volume')}")
        print("  ---")

    # 特別檢查 09:13:00.206805 附近的數據
    print("\n特別檢查 09:13:00.206 附近：")
    for item in data:
        if "09:13:00.20" in str(item.get('Datetime', '')):
            print(f"\n{item['Type']} at {item['Datetime']}:")
            if item['Type'] == 'Trade':
                print(f"  Price: {item.get('Price')}, Volume: {item.get('Volume')}, BS_Flag: {item.get('BS_Flag')}")
            else:
                print(f"  Bid1: {item.get('Bid1_Price')}, Ask1: {item.get('Ask1_Price')}")

except Exception as e:
    print(f"錯誤: {e}")