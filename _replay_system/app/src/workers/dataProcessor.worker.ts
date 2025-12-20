// Web Worker 用於在後台處理數據
import { ReplayRow, DepthRow, TradeRow } from '../types';

function parseDatetime(value: string | Date): Date {
  if (value instanceof Date) return value;
  return new Date(value);
}

function prepareReplayInWorker(rows: any[]): ReplayRow[] {
  // 過濾掉無效數據
  const validRows = rows.filter(r => r && r.Type && r.Timestamp && r.Datetime);

  const cloned: ReplayRow[] = validRows.map((r) => ({
    ...r,
    Datetime: parseDatetime(r.Datetime),
    BS_Flag: r.BS_Flag ?? 'None'
  }));

  cloned.sort((a, b) => {
    if (!a || !b) return 0;
    if (a.Timestamp === b.Timestamp) {
      if (a.Type === b.Type) return 0;
      return a.Type === 'Depth' ? -1 : 1;
    }
    return a.Timestamp - b.Timestamp;
  });

  let lastDepth: DepthRow | null = null;

  for (const row of cloned) {
    if (row.Type === 'Depth') {
      lastDepth = row as DepthRow;
      row.BS_Flag = 'None';
    } else if (row.Type === 'Trade' && lastDepth) {
      const trade = row as TradeRow;
      const price = Number(trade.Price ?? 0);
      const ask1 = Number(lastDepth.Ask1_Price ?? 0);
      const bid1 = Number(lastDepth.Bid1_Price ?? 0);
      if (price >= ask1) trade.BS_Flag = 'Out';
      else if (price <= bid1) trade.BS_Flag = 'In';
      else trade.BS_Flag = 'None';
    }
  }

  return cloned;
}

// 監聽來自主線程的消息
self.onmessage = (e: MessageEvent) => {
  const { type, data } = e.data;

  if (type === 'PREPARE_REPLAY') {
    try {
      const result = prepareReplayInWorker(data);
      self.postMessage({ type: 'PREPARE_REPLAY_SUCCESS', data: result });
    } catch (error) {
      self.postMessage({ type: 'PREPARE_REPLAY_ERROR', error: (error as Error).message });
    }
  }
};
