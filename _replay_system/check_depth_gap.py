import json

file_path = '5309_1219.json'
start_ts = 91841279001
end_ts = 91841355479

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"搜尋時間區間: {start_ts} 到 {end_ts} 之間的 Depth 更新...")
    
    found_depth = False
    if isinstance(data, list):
        for item in data:
            ts = item.get('Timestamp')
            if ts > start_ts and ts < end_ts:
                if item.get('Type') == 'Depth':
                    print(json.dumps(item, indent=2, ensure_ascii=False))
                    found_depth = True
    
    if not found_depth:
        print("此區間內無 Depth 更新。")

except Exception as e:
    print(f"錯誤: {e}")
