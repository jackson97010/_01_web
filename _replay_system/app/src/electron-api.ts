// Electron API bridge for renderer process
let ipcRenderer: any = null;

// Check if we're in Electron environment
if (typeof window !== 'undefined' && window.require) {
  try {
    const electron = window.require('electron');
    ipcRenderer = electron.ipcRenderer;
  } catch (e) {
    console.warn('Failed to load electron:', e);
  }
}

// Create the electronAPI interface
// Check if electronAPI is already defined
if (!window.electronAPI) {
  const api = ipcRenderer ? {
    pickFile: () => ipcRenderer.invoke('select-file'),
    loadFile: (filePath: string) => ipcRenderer.invoke('load-json-file', filePath),
    // Add stub methods for live stream features (not implemented yet)
    getAvailableStocks: async () => [],
    onMarketDataUpdate: (callback: any) => () => {},
    startLiveStream: async (stock: string) => ({ success: false, message: 'Not implemented' }),
    stopLiveStream: async () => ({ success: false, message: 'Not implemented' })
  } : {
    // Fallback for development without Electron
    pickFile: async () => null,
    loadFile: async (filePath: string) => {
      const response = await fetch(filePath);
      return response.json();
    },
    getAvailableStocks: async () => [],
    onMarketDataUpdate: (callback: any) => () => {},
    startLiveStream: async (stock: string) => ({ success: false, message: 'Not implemented' }),
    stopLiveStream: async () => ({ success: false, message: 'Not implemented' })
  };

  if (!ipcRenderer) {
    console.warn('Running without Electron - using mock API');
  }

  // Use Object.defineProperty to create the property
  Object.defineProperty(window, 'electronAPI', {
    value: api,
    writable: false,
    configurable: false
  });
}

export {};