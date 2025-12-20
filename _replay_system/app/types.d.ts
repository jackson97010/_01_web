export interface ElectronAPI {
  pickFile: () => Promise<string | null>;
  loadFile: (filePath: string) => Promise<any[]>;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}

export {};
