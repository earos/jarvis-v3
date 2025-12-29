import WebSocket from 'ws';
import { config } from './config';

export type WSEventType = 'system' | 'doorbell' | 'motion' | 'alert';

export interface WSMessage {
  type: WSEventType;
  data: any;
  timestamp?: string;
}

export class JarvisWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private isConnected = false;
  private eventHandlers: Map<WSEventType, ((data: any) => void)[]> = new Map();
  private connectionHandlers: ((connected: boolean) => void)[] = [];

  constructor() {
    this.connect();
  }

  private connect(): void {
    try {
      console.log(`[WebSocket] Connecting to ${config.wsUrl}...`);
      this.ws = new WebSocket(config.wsUrl);

      this.ws.on('open', () => {
        console.log('[WebSocket] Connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.notifyConnectionHandlers(true);
      });

      this.ws.on('message', (data: WebSocket.Data) => {
        try {
          const message: WSMessage = JSON.parse(data.toString());
          console.log('[WebSocket] Received:', message);
          this.handleMessage(message);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      });

      this.ws.on('close', () => {
        console.log('[WebSocket] Disconnected');
        this.isConnected = false;
        this.notifyConnectionHandlers(false);
        this.scheduleReconnect();
      });

      this.ws.on('error', (error) => {
        console.error('[WebSocket] Error:', error);
      });
    } catch (error) {
      console.error('[WebSocket] Connection error:', error);
      this.scheduleReconnect();
    }
  }

  private handleMessage(message: WSMessage): void {
    const handlers = this.eventHandlers.get(message.type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message.data);
        } catch (error) {
          console.error(`[WebSocket] Handler error for ${message.type}:`, error);
        }
      });
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    if (this.reconnectAttempts < config.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`[WebSocket] Reconnecting in ${config.reconnectInterval}ms (attempt ${this.reconnectAttempts}/${config.maxReconnectAttempts})`);

      this.reconnectTimer = setTimeout(() => {
        this.connect();
      }, config.reconnectInterval);
    } else {
      console.error('[WebSocket] Max reconnect attempts reached');
    }
  }

  public on(eventType: WSEventType, handler: (data: any) => void): void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, []);
    }
    this.eventHandlers.get(eventType)!.push(handler);
  }

  public onConnectionChange(handler: (connected: boolean) => void): void {
    this.connectionHandlers.push(handler);
  }

  private notifyConnectionHandlers(connected: boolean): void {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(connected);
      } catch (error) {
        console.error('[WebSocket] Connection handler error:', error);
      }
    });
  }

  public send(message: WSMessage): void {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Cannot send message, not connected');
    }
  }

  public getConnectionStatus(): boolean {
    return this.isConnected;
  }

  public disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
