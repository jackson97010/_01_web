import json

file_path = '5309_1219.json'
target_time = '09:18:41.355479'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    found = False
    # 假設這是一個列表，我們遍歷它
    if isinstance(data, list):
        for item in data:
            # 檢查時間戳欄位，通常可能是 'Time', 'time', 'Timestamp' 等
            # 我們先印出第一個項目的 keys 來確認結構，然後找目標
            
            # 嘗試匹配時間
            # 假設時間在某個欄位中，我們把所有值轉成字串來搜尋，或者直接看常見欄位
            # 但為了精確，我們先找時間
            item_str = str(item)
            if target_time in item_str:
                print(f"找到目標時間 {target_time} 的資料:")
                print(json.dumps(item, indent=2, ensure_ascii=False))
                found = True
                # 我們可以找找看前後幾筆資料來協助判斷趨勢（如果需要）
                
    if not found:
        print(f"在檔案中找不到時間為 {target_time} 的資料。")
        # 如果找不到，印出前幾筆資料結構幫助除錯
        if isinstance(data, list) and len(data) > 0:
            print("\n檔案結構範例 (第一筆):")
            print(json.dumps(data[0], indent=2, ensure_ascii=False))

except Exception as e:
    print(f"讀取或處理檔案時發生錯誤: {e}")
