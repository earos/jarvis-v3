import { BrowserWindow, screen } from 'electron';
import * as path from 'path';

let quickChatWindow: BrowserWindow | null = null;
let doorbellWindow: BrowserWindow | null = null;

export function createQuickChatWindow(): BrowserWindow {
  if (quickChatWindow) {
    return quickChatWindow;
  }
  
  // Get primary display dimensions
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  
  quickChatWindow = new BrowserWindow({
    width: 400,
    height: 500,
    x: width - 420,
    y: 40,
    show: false,
    frame: false,
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    transparent: false,
    backgroundColor: '#1a1a1a',
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });
  
  quickChatWindow.setTitle('JARVIS Quick Chat');
  quickChatWindow.loadFile(path.join(__dirname, '../renderer/quick-chat.html'));
  
  // Hide window when it loses focus
  quickChatWindow.on('blur', () => {
    if (quickChatWindow && !quickChatWindow.webContents.isDevToolsOpened()) {
      quickChatWindow.hide();
    }
  });
  
  quickChatWindow.on('closed', () => {
    quickChatWindow = null;
  });
  
  return quickChatWindow;
}

export function createDoorbellWindow(cameraUrl: string): BrowserWindow {
  // Close existing doorbell window if any
  if (doorbellWindow) {
    doorbellWindow.close();
  }
  
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  
  doorbellWindow = new BrowserWindow({
    width: 500,
    height: 600,
    x: width - 520,
    y: height - 650,
    show: true,
    frame: true,
    resizable: false,
    skipTaskbar: false,
    alwaysOnTop: true,
    title: 'JARVIS - Doorbell Alert',
    backgroundColor: '#1a1a1a',
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });
  
  doorbellWindow.loadFile(path.join(__dirname, '../renderer/doorbell.html'));
  
  // Send camera URL to renderer
  doorbellWindow.webContents.on('did-finish-load', () => {
    doorbellWindow?.webContents.send('doorbell-data', { cameraUrl });
  });
  
  // Auto-close after 30 seconds
  setTimeout(() => {
    if (doorbellWindow) {
      doorbellWindow.close();
    }
  }, 30000);
  
  doorbellWindow.on('closed', () => {
    doorbellWindow = null;
  });
  
  return doorbellWindow;
}

export function getQuickChatWindow(): BrowserWindow | null {
  return quickChatWindow;
}

export function getDoorbellWindow(): BrowserWindow | null {
  return doorbellWindow;
}
