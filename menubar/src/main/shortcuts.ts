import { app, globalShortcut } from 'electron';
import { config } from './config';

export class ShortcutManager {
  private registered = false;

  constructor(private onQuickChat: () => void) {
    this.registerShortcuts();
  }

  private registerShortcuts(): void {
    app.whenReady().then(() => {
      const ret = globalShortcut.register(config.globalShortcut, () => {
        console.log(`[Shortcut] ${config.globalShortcut} pressed`);
        this.onQuickChat();
      });

      if (ret) {
        console.log(`[Shortcut] Registered: ${config.globalShortcut}`);
        this.registered = true;
      } else {
        console.error(`[Shortcut] Failed to register: ${config.globalShortcut}`);
      }
    });
  }

  public isRegistered(): boolean {
    return this.registered;
  }

  public unregisterAll(): void {
    globalShortcut.unregisterAll();
    this.registered = false;
    console.log('[Shortcut] All shortcuts unregistered');
  }
}
