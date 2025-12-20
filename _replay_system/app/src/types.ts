export type DepthRow = {
  Type: 'Depth';
  Timestamp: number;
  Datetime: string | Date;
  BS_Flag?: 'None';
  [key: string]: any;
};

export type TradeRow = {
  Type: 'Trade';
  Timestamp: number;
  Datetime: string | Date;
  Price?: number;
  Volume?: number;
  BS_Flag?: 'In' | 'Out' | 'None';
};

export type ReplayRow = DepthRow | TradeRow;

export type StateAtIndex = {
  lastDepth: DepthRow | null;
  prevDepth: DepthRow | null;
  lastTrade: TradeRow | null;
};
