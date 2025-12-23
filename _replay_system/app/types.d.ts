export interface ElectronAPI {
  pickFile: () => Promise<string | null>;
  loadFile: (filePath: string) => Promise<any[]>;
  getAvailableStocks: () => Promise<string[]>;
  onMarketDataUpdate: (callback: (data: any) => void) => () => void;
  startLiveStream: (stock: string) => Promise<{ success: boolean; message: string }>;
  stopLiveStream: () => Promise<{ success: boolean; message: string }>;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
    require?: any;  // For Electron's require in renderer process
  }
}

export {};
