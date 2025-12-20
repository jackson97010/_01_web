import json
import sys

# 檢查 JSON 文件的前幾筆數據
file_path = r"C:\Users\User\Documents\HFT\_replay_system\2344_1219.json"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"總共 {len(data)} 筆數據")
    print("\n前 10 筆數據：")

    for i, item in enumerate(data[:10]):
        print(f"\n第 {i+1} 筆:")
        print(f"  Type: {item.get('Type')}")
        print(f"  Timestamp: {item.get('Timestamp')}")

        if item.get('Type') == 'Depth':
            print(f"  Bid1_Price: {item.get('Bid1_Price')}")
            print(f"  Bid1_Volume: {item.get('Bid1_Volume')}")
            print(f"  Ask1_Price: {item.get('Ask1_Price')}")
            print(f"  Ask1_Volume: {item.get('Ask1_Volume')}")
        elif item.get('Type') == 'Trade':
            print(f"  Price: {item.get('Price')}")
            print(f"  Volume: {item.get('Volume')}")
            print(f"  BS_Flag: {item.get('BS_Flag')}")

except Exception as e:
    print(f"錯誤: {e}")