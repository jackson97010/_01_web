import { DepthRow, TradeRow } from '../types';

/**
 * 解析即時串流的五檔資料
 * 格式：Depth,2355,131219825776,BID:5,333000*27,332500*5,332000*32,331500*35,331000*62,ASK:5,333500*17,334000*5,334500*13,335000*44,335500*14
 */
export function parseStreamDepth(line: string): DepthRow | null {
  // 防呆處理
  if (!line || !line.startsWith("Depth")) {
    return null;
  }

  // 拆解欄位
  const parts = line.split(',').map(x => x.trim());
  if (parts.length < 7) {
    return null; // 欄位不足時回傳 null
  }

  const timestamp = parseInt(parts[2]);
  const result: DepthRow = {
    Type: 'Depth',
    StockCode: parts[1].trim(),
    Timestamp: timestamp,
    Datetime: convertTimestampToDatetime(timestamp),
    BS_Flag: 'None',
    Price: null,
    Volume: null,
    Flag: null,
    TotalVolume: null,
    BidCount: 0,
    AskCount: 0,
    // 初始化五檔價格和數量
    Bid1_Price: 0, Bid1_Volume: 0,
    Bid2_Price: 0, Bid2_Volume: 0,
    Bid3_Price: 0, Bid3_Volume: 0,
    Bid4_Price: 0, Bid4_Volume: 0,
    Bid5_Price: 0, Bid5_Volume: 0,
    Ask1_Price: 0, Ask1_Volume: 0,
    Ask2_Price: 0, Ask2_Volume: 0,
    Ask3_Price: 0, Ask3_Volume: 0,
    Ask4_Price: 0, Ask4_Volume: 0,
    Ask5_Price: 0, Ask5_Volume: 0,
  };

  let bidIdx = 1;
  let askIdx = 1;
  let side: 'BID' | 'ASK' | null = null;

  // 找出 BID/ASK 區段
  for (let i = 3; i < parts.length; i++) {
    const part = parts[i];

    if (part.startsWith("BID:")) {
      side = 'BID';
      result.BidCount = parseInt(part.split(":")[1]);
    } else if (part.startsWith("ASK:")) {
      side = 'ASK';
      result.AskCount = parseInt(part.split(":")[1]);
    } else if (part.includes('*')) {
      // 處理價格*數量
      const [priceStr, qtyStr] = part.split('*');
      const price = parseInt(priceStr) / 10000; // 價格需要除以 10000
      const qty = parseInt(qtyStr);

      if (side === 'BID' && bidIdx <= 5) {
        (result as any)[`Bid${bidIdx}_Price`] = price;
        (result as any)[`Bid${bidIdx}_Volume`] = qty;
        bidIdx++;
      } else if (side === 'ASK' && askIdx <= 5) {
        (result as any)[`Ask${askIdx}_Price`] = price;
        (result as any)[`Ask${askIdx}_Volume`] = qty;
        askIdx++;
      }
    }
  }

  console.log('Parsed stream depth:', {
    StockCode: result.StockCode,
    Timestamp: result.Timestamp,
    Bid1: `${result.Bid1_Price} x ${result.Bid1_Volume}`,
    Ask1: `${result.Ask1_Price} x ${result.Ask1_Volume}`
  });

  return result;
}

/**
 * 解析即時串流的成交資料
 * 格式：Trade,2355,131219825776,333500,10,Out
 */
export function parseStreamTrade(line: string): TradeRow | null {
  if (!line || !line.startsWith("Trade")) {
    return null;
  }

  const parts = line.split(',').map(x => x.trim());
  if (parts.length < 5) {
    return null;
  }

  const timestamp = parseInt(parts[2]);
  const price = parseInt(parts[3]) / 10000;
  const volume = parseInt(parts[4]);
  const bsFlag = parts[5] || 'None';

  const result: TradeRow = {
    Type: 'Trade',
    StockCode: parts[1].trim(),
    Timestamp: timestamp,
    Datetime: convertTimestampToDatetime(timestamp),
    Price: price,
    Volume: volume,
    BS_Flag: bsFlag as 'In' | 'Out' | 'None',
    Flag: null,
    TotalVolume: null
  };

  console.log('Parsed stream trade:', {
    StockCode: result.StockCode,
    Timestamp: result.Timestamp,
    Price: result.Price,
    Volume: result.Volume,
    BS_Flag: result.BS_Flag
  });

  return result;
}

/**
 * 解析即時串流的一行資料
 */
export function parseStreamLine(line: string): DepthRow | TradeRow | null {
  if (line.startsWith('Depth')) {
    return parseStreamDepth(line);
  } else if (line.startsWith('Trade')) {
    return parseStreamTrade(line);
  }
  return null;
}

/**
 * 將 Timestamp (HHMMSSffffff) 轉換為 Datetime 字串
 */
function convertTimestampToDatetime(timestamp: number): string {
  const today = new Date();
  const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

  const tsStr = timestamp.toString().padStart(12, '0');
  const hours = tsStr.slice(0, 2);
  const minutes = tsStr.slice(2, 4);
  const seconds = tsStr.slice(4, 6);
  const micros = tsStr.slice(6, 12);

  return `${dateStr} ${hours}:${minutes}:${seconds}.${micros}`;
}

// 測試函數
export function testStreamParser(): void {
  console.log('=== 測試即時串流解析器 ===');

  // 測試五檔解析
  const depthLine = "Depth,2355  ,131219825776,BID:5,333000*27,332500*5,332000*32,331500*35,331000*62,ASK:5,333500*17,334000*5,334500*13,335000*44,335500*14";
  const depth = parseStreamDepth(depthLine);
  if (depth) {
    console.log('✓ 五檔解析成功');
    console.log('  Bid1:', depth.Bid1_Price, 'x', depth.Bid1_Volume);
    console.log('  Ask1:', depth.Ask1_Price, 'x', depth.Ask1_Volume);
  }

  // 測試成交解析
  const tradeLine = "Trade,2355,131219825776,333500,10,Out";
  const trade = parseStreamTrade(tradeLine);
  if (trade) {
    console.log('✓ 成交解析成功');
    console.log('  Price:', trade.Price);
    console.log('  Volume:', trade.Volume);
    console.log('  BS_Flag:', trade.BS_Flag);
  }
}