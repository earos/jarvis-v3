const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('jarvisAPI', {
  sendChat: (message) => ipcRenderer.invoke('send-chat', message),
  getConnectionStatus: () => ipcRenderer.invoke('get-connection-status'),
  onChatChunk: (callback) => ipcRenderer.on('chat-chunk', (event, chunk) => callback(chunk)),
  onConnectionStatus: (callback) => ipcRenderer.on('connection-status', (event, status) => callback(status)),
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel)
});
