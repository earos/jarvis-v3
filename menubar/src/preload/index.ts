import { contextBridge, ipcRenderer } from 'electron';

// Expose protected methods that allow the renderer process to use
// ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('jarvisAPI', {
  // Send message to JARVIS
  sendMessage: (message: string) => {
    ipcRenderer.send('send-message', message);
  },
  
  // Listen for JARVIS responses
  onResponse: (callback: (data: any) => void) => {
    ipcRenderer.on('jarvis-response', (_event, data) => callback(data));
  },
  
  // Listen for doorbell data
  onDoorbellData: (callback: (data: any) => void) => {
    ipcRenderer.on('doorbell-data', (_event, data) => callback(data));
  },
  
  // Window controls
  closeWindow: () => {
    ipcRenderer.send('close-window');
  },
  
  minimizeWindow: () => {
    ipcRenderer.send('minimize-window');
  }
});

// Handle window controls
ipcRenderer.on('close-window', () => {
  window.close();
});
