import { ReplayRow, StateAtIndex, DepthRow, TradeRow } from '../types';

export function prepareReplay(rows: any[]): ReplayRow[] {
  console.log('prepareReplay called with rows:', rows.length);

  // 過濾掉無效數據
  const validRows = rows.filter(r => r && r.Type && r.Timestamp && r.Datetime);
  console.log('Valid rows after filter:', validRows.length);

  // Check data types
  const depthCount = validRows.filter(r => r.Type === 'Depth').length;
  const tradeCount = validRows.filter(r => r.Type === 'Trade').length;
  console.log(`prepareReplay: ${depthCount} Depth, ${tradeCount} Trade`);

  const cloned: ReplayRow[] = validRows.map((r) => ({
    ...r,
    // 保留原始的 Datetime 字串格式，以保持微秒精度
    Datetime: r.Datetime,
    BS_Flag: r.BS_Flag ?? 'None'
  }));

  cloned.sort((a, b) => {
    if (!a || !b) return 0;
    if (a.Timestamp === b.Timestamp) {
      if (a.Type === b.Type) return 0;
      // 當時間相同時，Depth 排在 Trade 前面
      // 這樣當處理 Trade 時，同時間的 Depth 已經是 lastDepth
      return a.Type === 'Depth' ? -1 : 1;
    }
    return a.Timestamp - b.Timestamp;
  });

  let lastDepth: DepthRow | null = null;
  let lastTrade: TradeRow | null = null; // 追蹤上一筆成交，用於 Tick Rule

  for (const row of cloned) {
    if (row.Type === 'Depth') {
      lastDepth = row as DepthRow;
      // Depth 的 BS_Flag 保持為 'None'
      if (!row.BS_Flag) {
        row.BS_Flag = 'None';
      }
    } else if (row.Type === 'Trade') {
      const trade = row as TradeRow;

      // 如果 JSON 已經有 BS_Flag，就不要重新計算
      // 使用 as any 來避免 TypeScript 類型檢查錯誤
      const bsFlag = trade.BS_Flag as any;
      if (!bsFlag || bsFlag === '' || bsFlag === 'Unknown') {
        // 只有在沒有 BS_Flag 時才計算
        if (lastDepth) {
          const price = Number(trade.Price ?? 0);
          const ask1 = Number(lastDepth.Ask1_Price ?? 0);
          const bid1 = Number(lastDepth.Bid1_Price ?? 0);

          if (price >= ask1 && ask1 > 0) {
            trade.BS_Flag = 'Out';
          } else if (price <= bid1 && bid1 > 0) {
            trade.BS_Flag = 'In';
          } else {
            // 價格在中間，使用 Tick Rule (與上一筆成交價比較)
            if (lastTrade && lastTrade.Price !== undefined) {
              const prevPrice = Number(lastTrade.Price);
              if (price > prevPrice) {
                trade.BS_Flag = 'Out';
              } else if (price < prevPrice) {
                trade.BS_Flag = 'In';
              } else {
                // 價格相同，延續上一筆的方向
                trade.BS_Flag = lastTrade.BS_Flag;
              }
            } else {
              trade.BS_Flag = 'None';
            }
          }
        } else {
          trade.BS_Flag = 'None';
        }
      }

      // 更新上一筆成交
      lastTrade = trade;

      // 調試：記錄判斷邏輯
      if (trade.Timestamp === 90111319589) {
        console.log('Debug 09:01:11.319589:', {
          originalBS: trade.BS_Flag,
          price: trade.Price,
          fromJSON: true
        });
      }
    }
  }

  return cloned;
}

export function getStateAtIndex(data: ReplayRow[], idx: number): StateAtIndex {
  console.log(`getStateAtIndex called with data.length=${data?.length}, idx=${idx}`);

  if (!data || data.length === 0) {
    console.log('No data available');
    return { lastDepth: null, prevDepth: null, lastTrade: null };
  }

  const clamped = Math.max(0, Math.min(idx, data.length - 1));
  let lastDepth: DepthRow | null = null;
  let prevDepth: DepthRow | null = null;
  let lastTrade: TradeRow | null = null;
  let depthCount = 0;
  let tradeCount = 0;

  for (let i = 0; i <= clamped; i += 1) {
    const row = data[i];
    if (!row || !row.Type) continue; // 跳過無效數據

    if (row.Type === 'Depth') {
      prevDepth = lastDepth;
      lastDepth = row as DepthRow;
      depthCount++;
    } else if (row.Type === 'Trade') {
      lastTrade = row as TradeRow;
      tradeCount++;
    }
  }

  console.log(`getStateAtIndex: processed ${depthCount} Depth and ${tradeCount} Trade rows up to index ${clamped}`);
  console.log('lastDepth:', lastDepth ? 'Found' : 'Not found');

  if (lastDepth) {
    console.log('Depth data sample:', {
      Bid1_Price: lastDepth.Bid1_Price,
      Ask1_Price: lastDepth.Ask1_Price,
      Type: lastDepth.Type
    });
  }

  return { lastDepth, prevDepth, lastTrade };
}
