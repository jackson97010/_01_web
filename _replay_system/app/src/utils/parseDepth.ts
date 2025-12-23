// 解析原始五檔資料格式
export interface RawDepthData {
  Type: string;
  StockCode: string;
  Timestamp: number;
  BidCount: number;
  AskCount: number;
  Bids: Array<{ price: number; volume: number }>;
  Asks: Array<{ price: number; volume: number }>;
}

export function parseDepthLine(line: string): any {
  /**
   * 解析五檔
   * 收到： Depth,2355  ,131219825776,BID:5,333000*27,332500*5,332000*32,331500*35,331000*62,ASK:5,333500*17,334000*5,334500*13,335000*44,335500*14
   * 解析：Depth,股票代碼,報價時間,BID:委買檔數,第1檔價格*數量,第2檔價格*數量,第3檔價格*數量,第4檔價格*數量,第5檔價格*數量,
   *         ASK:委賣檔數,第1檔價格*數量,第2檔價格*數量,第3檔價格*數量,第4檔價格*數量,第5檔價格*數量
   */

  // 防呆處理
  if (!line || !line.startsWith("Depth")) {
    return null;
  }

  // 拆解欄位
  const parts = line.split(',').map(x => x.trim());
  if (parts.length < 7) {
    return null; // 欄位不足時回傳 null
  }

  const result: any = {
    Type: 'Depth',
    StockCode: parts[1].trim(),
    Timestamp: parseInt(parts[2]),
    Datetime: '', // 需要轉換
  };

  let bidIdx = 1;
  let askIdx = 1;
  let side: 'BID' | 'ASK' | null = null;

  // 找出 BID/ASK 區段
  for (let i = 3; i < parts.length; i++) {
    const part = parts[i];

    if (part.startsWith("BID:")) {
      side = 'BID';
      const bidCount = parseInt(part.split(":")[1]);
      result.BidCount = bidCount;
    } else if (part.startsWith("ASK:")) {
      side = 'ASK';
      const askCount = parseInt(part.split(":")[1]);
      result.AskCount = askCount;
    } else if (part.includes('*')) {
      // 處理價格*數量
      const [priceStr, qtyStr] = part.split('*');
      const price = parseInt(priceStr) / 10000; // 價格需要除以 10000
      const qty = parseInt(qtyStr);

      if (side === 'BID') {
        result[`Bid${bidIdx}_Price`] = price;
        result[`Bid${bidIdx}_Volume`] = qty;
        bidIdx++;
      } else if (side === 'ASK') {
        result[`Ask${askIdx}_Price`] = price;
        result[`Ask${askIdx}_Volume`] = qty;
        askIdx++;
      }
    }
  }

  // 補齊五檔（如果不足五檔）
  for (let i = bidIdx; i <= 5; i++) {
    result[`Bid${i}_Price`] = 0;
    result[`Bid${i}_Volume`] = 0;
  }
  for (let i = askIdx; i <= 5; i++) {
    result[`Ask${i}_Price`] = 0;
    result[`Ask${i}_Volume`] = 0;
  }

  // 加入其他可能需要的欄位
  result.BS_Flag = 'None';
  result.Price = null;
  result.Volume = null;

  return result;
}

// 將 Timestamp (HHMMSSffffff) 轉換為 Datetime 字串
export function convertTimestampToDatetime(timestamp: number, dateStr: string = '2025-12-19'): string {
  const tsStr = timestamp.toString().padStart(12, '0');
  const hours = tsStr.slice(0, 2);
  const minutes = tsStr.slice(2, 4);
  const seconds = tsStr.slice(4, 6);
  const micros = tsStr.slice(6, 12);

  return `${dateStr} ${hours}:${minutes}:${seconds}.${micros}`;
}

// 測試函數
export function testParseDepth(): void {
  const testLine = "Depth,2355  ,131219825776,BID:5,333000*27,332500*5,332000*32,331500*35,331000*62,ASK:5,333500*17,334000*5,334500*13,335000*44,335500*14";
  const result = parseDepthLine(testLine);

  if (result) {
    console.log('Parse result:', result);
    console.log('Bid1:', result.Bid1_Price, 'x', result.Bid1_Volume);
    console.log('Ask1:', result.Ask1_Price, 'x', result.Ask1_Volume);
  }
}