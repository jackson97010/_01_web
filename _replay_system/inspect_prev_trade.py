import json

file_path = '5309_1219.json'
target_timestamp = 91841355479  # 使用整數時間戳比較更準確

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    last_trade = None
    target_trade = None
    
    if isinstance(data, list):
        # 排序以確保順序（雖然通常是排好的，但保險起見）
        # data.sort(key=lambda x: x.get('Timestamp', 0)) 
        # 先假設檔案已經是時間排序的，因為排序44MB可能稍慢且如果原檔有特定順序邏輯不想破壞
        
        for item in data:
            current_ts = item.get('Timestamp')
            
            # 找到目標那筆 Trade
            if current_ts == target_timestamp and item.get('Type') == 'Trade':
                target_trade = item
                print(f"--- 目標成交 (Timestamp: {current_ts}) ---")
                print(json.dumps(item, indent=2, ensure_ascii=False))
                
                if last_trade:
                    print(f"\n--- 上一筆成交 (Timestamp: {last_trade.get('Timestamp')}) ---")
                    print(json.dumps(last_trade, indent=2, ensure_ascii=False))
                else:
                    print("\n找不到上一筆成交資料。")
                break # 找到後可以停止，或者繼續看有沒有重複的
            
            # 更新上一筆 Trade
            if item.get('Type') == 'Trade':
                last_trade = item

    if not target_trade:
        print(f"未找到 Timestamp 為 {target_timestamp} 的 Trade 資料。")

except Exception as e:
    print(f"錯誤: {e}")
