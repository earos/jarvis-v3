# JARVIS Menu Bar App

A native macOS menu bar application for JARVIS v3, providing quick access to your homelab AI assistant.

## Features

- **System Tray Icon**: Always-visible menu bar icon with connection status indicator
- **Quick Chat**: Instant access via `Cmd+Shift+J` global shortcut
- **Real-time Alerts**: Native macOS notifications for doorbell and motion events
- **WebSocket Integration**: Live connection to JARVIS backend for instant updates
- **Minimal UI**: Clean, native-feeling interface that stays out of your way

## Prerequisites

- macOS 10.13 or later
- Node.js 18+ and npm
- Access to JARVIS backend server at `192.168.10.100:3939`

## Installation

### 1. Clone/Copy Files

The app is located at `/opt/jarvis-v3/menubar/` on the server.

### 2. Install Dependencies

```bash
cd /opt/jarvis-v3/menubar
npm install
```

### 3. Build the App

```bash
npm run build
```

Or use the build script:

```bash
chmod +x build.sh
./build.sh
```

## Running the App

### Development Mode

```bash
npm run dev
```

This will compile TypeScript and start the Electron app.

### Production Mode

```bash
npm start
```

## Building Distributable

To create a macOS app bundle and DMG installer:

```bash
npm run dist
```

The built app will be in the `build/` directory.

To create an unsigned development build:

```bash
npm run pack
```

## Usage

### Quick Chat

1. Press `Cmd+Shift+J` from anywhere on your Mac
2. Type your question in the chat window
3. Press Enter to send (Shift+Enter for new line)
4. The window will stay on top for quick access

### Tray Menu

Click the JARVIS icon in the menu bar to access:

- **Quick Chat**: Open the chat window
- **Open Dashboard**: Opens JARVIS web dashboard in your browser
- **Homelab Status**: View server and WebSocket connection status
- **Settings**: App configuration (future feature)
- **Quit**: Exit the application

### Connection Status

The tray icon color indicates connection status:
- **Green**: Connected to JARVIS backend
- **Red**: Disconnected

### Notifications

The app automatically shows macOS notifications for:

- **Doorbell Events**: When someone rings the doorbell
- **Motion Detection**: When security cameras detect motion
- **System Alerts**: Important JARVIS notifications

## Configuration

Edit `src/main/config.ts` to change:

```typescript
export const config = {
  serverUrl: 'http://192.168.10.100:3939',
  wsUrl: 'ws://192.168.10.100:3939/ws',
  chatEndpoint: '/api/chat/v2',
  dashboardUrl: 'http://192.168.10.100:3939',
  globalShortcut: 'CommandOrControl+Shift+J',
  reconnectInterval: 5000,
  maxReconnectAttempts: 10
};
```

After changing configuration, rebuild the app:

```bash
npm run build
```

## Project Structure

```
menubar/
├── src/
│   ├── main/
│   │   ├── index.ts        # Main process entry point
│   │   ├── config.ts       # App configuration
│   │   ├── websocket.ts    # WebSocket client
│   │   ├── tray.ts         # System tray management
│   │   └── shortcuts.ts    # Global keyboard shortcuts
│   └── renderer/
│       ├── preload.js      # Preload script for IPC
│       ├── quickchat.html  # Chat window HTML
│       └── quickchat.js    # Chat window logic
├── dist/                   # Compiled JavaScript (generated)
├── build/                  # Distribution builds (generated)
├── package.json
├── tsconfig.json
└── README.md
```

## WebSocket Events

The app listens for these WebSocket event types:

- `system`: Connection status updates
- `doorbell`: Doorbell ring detected
- `motion`: Motion detection from cameras
- `alert`: General alerts from JARVIS

Event format:
```json
{
  "type": "doorbell",
  "data": {
    "camera_name": "Front Door",
    "event": {
      "camera_id": "abc123",
      "camera_name": "Front Door",
      "event_type": "ring",
      "timestamp": 1735480200000
    },
    "timestamp": "2025-12-29T10:30:00.000000"
  },
  "timestamp": 1735480200.0,
  "source": "unifi_protect"
}
```

## Chat API

The app uses the JARVIS v2 chat API with Server-Sent Events (SSE) streaming:

**Endpoint**: `POST http://192.168.10.100:3939/api/chat/v2`

**Request**:
```json
{
  "message": "What's the weather like?",
  "stream": true
}
```

**Response**: SSE stream with chunks:
```
data: {"type": "content", "content": "The "}
data: {"type": "content", "content": "weather "}
data: {"type": "content", "content": "is sunny!"}
data: {"type": "done"}
data: [DONE]
```

## Troubleshooting

### App Won't Start

1. Check that dependencies are installed: `npm install`
2. Rebuild TypeScript: `npm run build`
3. Check logs in Console.app (filter for "JARVIS")

### Can't Connect to Server

1. Verify server is accessible: `curl http://192.168.10.100:3939`
2. Check WebSocket: `wscat -c ws://192.168.10.100:3939/ws`
3. Verify firewall settings

### Global Shortcut Not Working

1. Grant Accessibility permissions in System Preferences > Security & Privacy > Accessibility
2. Check if another app is using `Cmd+Shift+J`
3. Try changing the shortcut in `config.ts`

### Notifications Not Showing

1. Grant notification permissions in System Preferences > Notifications
2. Check "Do Not Disturb" mode is off
3. Verify Focus modes aren't blocking notifications

## Development

### Watch Mode

For active development, use watch mode to auto-recompile TypeScript:

```bash
# Terminal 1: Watch and compile TypeScript
npm run watch

# Terminal 2: Run Electron (restart after changes)
npm start
```

### Debug Mode

Open DevTools in the Quick Chat window:

1. Add to `src/main/index.ts` in `createQuickChatWindow()`:
```typescript
this.quickChatWindow.webContents.openDevTools();
```

2. Rebuild and run

### Logs

View logs in Terminal when running with `npm start`, or check:
- macOS Console.app (filter: "JARVIS")
- `~/Library/Logs/JARVIS/`

## Building for Distribution

### Code Signing (Optional)

For distribution outside development, you'll need to sign the app:

1. Get an Apple Developer account
2. Generate certificates
3. Update `package.json` build config:

```json
{
  "build": {
    "mac": {
      "identity": "Developer ID Application: Your Name (TEAMID)"
    }
  }
}
```

### Notarization (Optional)

For macOS 10.15+, apps should be notarized:

```bash
npm run dist
xcrun notarytool submit build/JARVIS-1.0.0.dmg --keychain-profile "AC_PASSWORD"
```

## Future Enhancements

- [ ] Settings window for configuration
- [ ] Custom notification sounds
- [ ] Camera preview in alerts
- [ ] Chat history persistence
- [ ] Multiple conversation threads
- [ ] Auto-start on login
- [ ] System tray icon customization
- [ ] Keyboard shortcuts customization UI

## License

MIT

## Support

For issues or questions, contact the JARVIS homelab admin.
