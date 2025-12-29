import { app, Menu, Tray, nativeImage, shell, Notification } from 'electron';
import path from 'path';
import { config } from './config';

export class JarvisTray {
  private tray: Tray | null = null;
  private isConnected = false;
  private hasAlerts = false;

  constructor(private onQuickChatClick: () => void) {
    this.createTray();
  }

  private createTray(): void {
    // Create a simple colored circle as tray icon (macOS template image)
    const icon = this.createTrayIcon(false);
    this.tray = new Tray(icon);
    this.tray.setToolTip('JARVIS');
    this.updateMenu();

    this.tray.on('click', () => {
      this.onQuickChatClick();
    });
  }

  private createTrayIcon(connected: boolean): Electron.NativeImage {
    // For macOS, we create a simple template image
    // In production, you'd use actual icon files
    const size = 22;
    const canvas = Buffer.from(
      `<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
        <circle cx="${size/2}" cy="${size/2}" r="${size/2 - 2}"
                fill="${connected ? '#00FF00' : '#FF0000'}"
                stroke="#000000" stroke-width="2"/>
      </svg>`
    );

    const image = nativeImage.createFromBuffer(canvas);
    image.setTemplateImage(true);
    return image.resize({ width: 22, height: 22 });
  }

  private updateMenu(): void {
    if (!this.tray) return;

    const statusText = this.isConnected
      ? 'Connected'
      : 'Disconnected';

    const contextMenu = Menu.buildFromTemplate([
      {
        label: `JARVIS - ${statusText}`,
        enabled: false
      },
      { type: 'separator' },
      {
        label: 'Quick Chat',
        accelerator: 'CommandOrControl+Shift+J',
        click: () => this.onQuickChatClick()
      },
      {
        label: 'Open Dashboard',
        click: () => shell.openExternal(config.dashboardUrl)
      },
      { type: 'separator' },
      {
        label: 'Homelab Status',
        submenu: [
          {
            label: `Server: ${this.isConnected ? 'Online' : 'Offline'}`,
            enabled: false
          },
          {
            label: `WebSocket: ${this.isConnected ? 'Connected' : 'Disconnected'}`,
            enabled: false
          }
        ]
      },
      { type: 'separator' },
      {
        label: 'Settings',
        click: () => {
          // TODO: Open settings window
          console.log('Settings clicked');
        }
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => app.quit()
      }
    ]);

    this.tray.setContextMenu(contextMenu);
  }

  public setConnectionStatus(connected: boolean): void {
    this.isConnected = connected;
    if (this.tray) {
      const icon = this.createTrayIcon(connected);
      this.tray.setImage(icon);
      this.updateMenu();
    }
  }

  public showAlert(title: string, body: string): void {
    this.hasAlerts = true;

    // Show native notification
    const notification = new Notification({
      title,
      body,
      silent: false,
      urgency: 'critical'
    });

    notification.show();

    // Update icon to show alert state
    if (this.tray) {
      this.updateMenu();
    }
  }

  public clearAlerts(): void {
    this.hasAlerts = false;
    if (this.tray) {
      this.updateMenu();
    }
  }

  public destroy(): void {
    if (this.tray) {
      this.tray.destroy();
      this.tray = null;
    }
  }
}
