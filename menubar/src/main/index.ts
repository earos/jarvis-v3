import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import { JarvisWebSocket } from './websocket';
import { JarvisTray } from './tray';
import { ShortcutManager } from './shortcuts';
import { config } from './config';

class JarvisMenuBar {
  private mainWindow: BrowserWindow | null = null;
  private quickChatWindow: BrowserWindow | null = null;
  private wsClient: JarvisWebSocket;
  private tray: JarvisTray;
  private shortcutManager: ShortcutManager;

  constructor() {
    // Initialize WebSocket
    this.wsClient = new JarvisWebSocket();

    // Initialize Tray
    this.tray = new JarvisTray(() => this.toggleQuickChat());

    // Initialize Shortcuts
    this.shortcutManager = new ShortcutManager(() => this.toggleQuickChat());

    // Setup WebSocket event handlers
    this.setupWebSocketHandlers();

    // Setup IPC handlers
    this.setupIpcHandlers();
  }

  private setupWebSocketHandlers(): void {
    // Connection status
    this.wsClient.onConnectionChange((connected) => {
      console.log(`[App] Connection status changed: ${connected}`);
      this.tray.setConnectionStatus(connected);

      // Notify renderer if window is open
      if (this.quickChatWindow) {
        this.quickChatWindow.webContents.send('connection-status', connected);
      }
    });

    // Doorbell events
    this.wsClient.on('doorbell', (data) => {
      console.log('[App] Doorbell event:', data);
      this.tray.showAlert(
        'Doorbell',
        data.message || 'Someone is at the door!'
      );
    });

    // Motion events
    this.wsClient.on('motion', (data) => {
      console.log('[App] Motion event:', data);
      this.tray.showAlert(
        'Motion Detected',
        data.message || `Motion detected: ${data.camera || 'Unknown camera'}`
      );
    });

    // Alert events
    this.wsClient.on('alert', (data) => {
      console.log('[App] Alert event:', data);
      this.tray.showAlert(
        data.title || 'Alert',
        data.message || 'JARVIS alert'
      );
    });

    // System events
    this.wsClient.on('system', (data) => {
      console.log('[App] System event:', data);
    });
  }

  private setupIpcHandlers(): void {
    // Handle chat messages from renderer
    ipcMain.handle('send-chat', async (event, message: string) => {
      try {
        const response = await fetch(`${config.serverUrl}${config.chatEndpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message,
            stream: true
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No response body');
        }

        let fullResponse = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') continue;

              try {
                const parsed = JSON.parse(data);
                fullResponse += parsed.content || '';

                // Send chunk to renderer
                if (this.quickChatWindow) {
                  this.quickChatWindow.webContents.send('chat-chunk', parsed.content || '');
                }
              } catch (e) {
                // Ignore parse errors for SSE
              }
            }
          }
        }

        return { success: true, response: fullResponse };
      } catch (error) {
        console.error('[IPC] Chat error:', error);
        return { success: false, error: String(error) };
      }
    });

    // Get connection status
    ipcMain.handle('get-connection-status', () => {
      return this.wsClient.getConnectionStatus();
    });
  }

  private createQuickChatWindow(): void {
    if (this.quickChatWindow) {
      this.quickChatWindow.focus();
      return;
    }

    this.quickChatWindow = new BrowserWindow({
      width: 500,
      height: 600,
      show: false,
      frame: false,
      resizable: true,
      alwaysOnTop: true,
      skipTaskbar: true,
      transparent: false,
      backgroundColor: '#1e1e1e',
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, '../renderer/preload.js')
      }
    });

    this.quickChatWindow.loadFile(path.join(__dirname, '../renderer/quickchat.html'));

    this.quickChatWindow.on('blur', () => {
      // Auto-hide on blur (optional)
      // this.quickChatWindow?.hide();
    });

    this.quickChatWindow.on('closed', () => {
      this.quickChatWindow = null;
    });

    this.quickChatWindow.once('ready-to-show', () => {
      this.quickChatWindow?.show();
    });
  }

  private toggleQuickChat(): void {
    if (this.quickChatWindow && this.quickChatWindow.isVisible()) {
      this.quickChatWindow.hide();
    } else if (this.quickChatWindow) {
      this.quickChatWindow.show();
      this.quickChatWindow.focus();
    } else {
      this.createQuickChatWindow();
    }
  }

  public async init(): Promise<void> {
    // Don't quit when all windows are closed (menu bar app)
    app.on('window-all-closed', (e: Event) => {
      e.preventDefault();
    });

    app.on('before-quit', () => {
      this.wsClient.disconnect();
      this.shortcutManager.unregisterAll();
      this.tray.destroy();
    });
  }
}

// App initialization
app.whenReady().then(() => {
  const jarvisApp = new JarvisMenuBar();
  jarvisApp.init();
});

// Handle macOS dock icon
if (process.platform === 'darwin') {
  app.dock.hide();
}
