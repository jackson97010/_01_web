import Redis from 'ioredis';

// Redis 配置
const REDIS_CONFIG = {
  host: '192.168.100.130',
  port: 6379,
  retryStrategy: (times) => {
    const delay = Math.min(times * 50, 2000);
    return delay;
  },
  enableReadyCheck: true,
  maxRetriesPerRequest: 3
};

// 可用的股票代碼
const AVAILABLE_CHANNELS = ['4939', '8042', '2485', '6291'];

class MarketDataProcessor {
  constructor() {
    this.depthState = new Map(); // 儲存每個股票的最新五檔資訊
    this.tickBuffer = [];
    this.redis = null;
    this.isConnected = false;
    this.onDataCallback = null;
    this.bufferTimer = null;
    this.bufferInterval = 50; // 每 50ms 發送一次資料
    this.targetStockId = null; // 目標股票代碼
    this.subscribedChannels = []; // 實際訂閱的頻道
  }

  /**
   * 解析時間字串 (HHMMSSuuuuuu) 轉換為 timestamp
   * 例如: 131219825776 -> 13:12:19.825776
   */
  parseTime(timeStr) {
    const s = String(timeStr).trim().padStart(12, '0');

    // 解析各部分
    const hours = parseInt(s.substring(0, 2));
    const minutes = parseInt(s.substring(2, 4));
    const seconds = parseInt(s.substring(4, 6));
    const microseconds = parseInt(s.substring(6, 12));

    // 取得今天的日期
    const now = new Date();
    const date = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
      hours,
      minutes,
      seconds,
      Math.floor(microseconds / 1000) // 微秒轉毫秒
    );

    return date.getTime();
  }

  /**
   * 解析五檔資料並更新 Cache
   */
  parseDepth(line) {
    const parts = line.split(',').map(x => x.trim());
    if (parts.length < 4) return;

    const code = parts[1].trim();
    const timeStr = parts[2];

    let bestBid = 0;
    let bestAsk = 0;
    let currentSide = null;

    // 解析 BID/ASK 資料
    for (let i = 3; i < parts.length; i++) {
      const part = parts[i];

      if (part.startsWith('BID')) {
        currentSide = 'BID';
        continue;
      } else if (part.startsWith('ASK')) {
        currentSide = 'ASK';
        continue;
      }

      if (part.includes('*')) {
        try {
          const [priceStr] = part.split('*');
          const price = parseInt(priceStr) / 10000;

          if (currentSide === 'BID' && bestBid === 0) {
            bestBid = price;
          } else if (currentSide === 'ASK' && bestAsk === 0) {
            bestAsk = price;
          }
        } catch (e) {
          continue;
        }
      }
    }

    // 更新該股票的五檔狀態
    this.depthState.set(code, {
      timestamp: timeStr,
      bestBid: bestBid,
      bestAsk: bestAsk
    });
  }

  /**
   * 解析成交資料，結合 Cache 判斷內外盤
   */
  parseTrade(line) {
    const parts = line.split(',').map(x => x.trim());
    if (parts.length < 7) return null;

    const code = parts[1].trim();

    // 如果有指定目標股票，只處理該股票的資料
    if (this.targetStockId && code !== this.targetStockId) {
      return null;
    }

    const timeStr = parts[2];
    const simFlag = parseInt(parts[3]);

    let price, volume, totalVolume;
    try {
      price = parseInt(parts[4]) / 10000;
      volume = parseInt(parts[5]);
      totalVolume = parseInt(parts[6]);
    } catch (e) {
      return null;
    }

    // 內外盤判斷
    let tickType = 0; // 0: 中性, 1: 外盤(Buy), 2: 內盤(Sell)
    let refBid = 0;
    let refAsk = 0;

    if (this.depthState.has(code)) {
      const cache = this.depthState.get(code);
      refBid = cache.bestBid;
      refAsk = cache.bestAsk;

      if (refAsk > 0 && price >= refAsk) {
        tickType = 1; // 外盤
      } else if (refBid > 0 && price <= refBid) {
        tickType = 2; // 內盤
      }
    }

    // 建立 Tick 資料物件
    const tick = {
      code: code,
      timestamp: this.parseTime(timeStr),
      datetime: new Date(this.parseTime(timeStr)).toISOString(),
      price: price,
      volume: volume,
      totalVolume: totalVolume,
      tickType: tickType,
      BS_Flag: tickType === 1 ? 'Out' : (tickType === 2 ? 'In' : 'None'),
      refBidPrice: refBid,
      refAskPrice: refAsk,
      simTrade: simFlag
    };

    this.tickBuffer.push(tick);
    return tick;
  }

  /**
   * 啟動 Redis 連線與訂閱
   * @param {Function} callback - 資料回調函數
   * @param {string} stockId - 目標股票代碼（可選）
   */
  async connect(callback, stockId = null) {
    this.onDataCallback = callback;
    this.targetStockId = stockId;

    try {
      console.log(`Connecting to Redis ${REDIS_CONFIG.host}:${REDIS_CONFIG.port}...`);

      // 建立 Redis 連線
      this.redis = new Redis(REDIS_CONFIG);

      // 連線事件處理
      this.redis.on('connect', () => {
        console.log('Redis connected successfully');
        this.isConnected = true;
      });

      this.redis.on('error', (err) => {
        console.error('Redis connection error:', err);
        this.isConnected = false;
      });

      this.redis.on('close', () => {
        console.log('Redis connection closed');
        this.isConnected = false;
      });

      // 決定要訂閱的頻道
      if (stockId && AVAILABLE_CHANNELS.includes(stockId)) {
        // 只訂閱指定的股票
        this.subscribedChannels = [stockId];
        console.log(`Subscribing to single stock: ${stockId}`);
      } else if (stockId === 'ALL') {
        // 訂閱所有股票
        this.subscribedChannels = [...AVAILABLE_CHANNELS];
        this.targetStockId = null; // 清除過濾條件
        console.log('Subscribing to all stocks');
      } else {
        // 預設訂閱所有，但如果有指定股票ID則只處理該股票的資料
        this.subscribedChannels = [...AVAILABLE_CHANNELS];
        if (stockId) {
          console.log(`Subscribing to all channels but filtering for stock: ${stockId}`);
        } else {
          console.log('Subscribing to all stocks (default)');
        }
      }

      // 訂閱頻道
      await this.redis.subscribe(...this.subscribedChannels);
      console.log(`Subscribed to channels: ${this.subscribedChannels.join(', ')}`);

      // 處理訊息
      this.redis.on('message', (channel, message) => {
        this.handleMessage(message);
      });

      // 啟動資料緩衝發送
      this.startBufferTimer();

      return true;
    } catch (error) {
      console.error('Failed to connect to Redis:', error);
      this.isConnected = false;
      return false;
    }
  }

  /**
   * 處理 Redis 訊息
   */
  handleMessage(message) {
    try {
      // 處理五檔資料
      if (message.startsWith('depthLog')) {
        this.parseDepth(message);
      }
      // 處理成交資料
      else if (message.startsWith('Trade')) {
        const tick = this.parseTrade(message);
        if (tick) {
          // 不立即發送，而是加入緩衝區
          // 由 bufferTimer 統一發送
        }
      }
    } catch (error) {
      console.error('Error processing message:', error);
    }
  }

  /**
   * 啟動緩衝發送計時器
   */
  startBufferTimer() {
    if (this.bufferTimer) {
      clearInterval(this.bufferTimer);
    }

    this.bufferTimer = setInterval(() => {
      if (this.tickBuffer.length > 0 && this.onDataCallback) {
        // 發送緩衝區的資料
        const dataToSend = [...this.tickBuffer];
        this.tickBuffer = [];

        // 透過 callback 發送給 main process
        this.onDataCallback({
          type: 'tick-batch',
          data: dataToSend,
          timestamp: Date.now()
        });
      }
    }, this.bufferInterval);
  }

  /**
   * 斷開連線
   */
  async disconnect() {
    console.log('Disconnecting from Redis...');

    if (this.bufferTimer) {
      clearInterval(this.bufferTimer);
      this.bufferTimer = null;
    }

    if (this.redis && this.subscribedChannels.length > 0) {
      await this.redis.unsubscribe(...this.subscribedChannels);
      this.redis.disconnect();
      this.redis = null;
    }

    this.isConnected = false;
    this.depthState.clear();
    this.tickBuffer = [];
    this.targetStockId = null;
    this.subscribedChannels = [];
  }

  /**
   * 取得連線狀態
   */
  getStatus() {
    return {
      connected: this.isConnected,
      channelsSubscribed: this.subscribedChannels,
      targetStockId: this.targetStockId,
      depthCacheSize: this.depthState.size,
      bufferSize: this.tickBuffer.length
    };
  }

  /**
   * 取得可用的股票列表
   */
  static getAvailableStocks() {
    return AVAILABLE_CHANNELS;
  }
}

export default MarketDataProcessor;