# JARVIS Menu Bar App - Quick Installation Guide

## Step 1: Deploy to Server

From your local machine, run the deployment script:

```bash
chmod +x /tmp/jarvis-menubar-deploy.sh
/tmp/jarvis-menubar-deploy.sh
```

This will copy all files to the server at `/opt/jarvis-v3/menubar/`

## Step 2: Install on Server

SSH into the server:

```bash
ssh root@192.168.10.100
cd /opt/jarvis-v3/menubar
```

Install Node.js dependencies:

```bash
npm install
```

## Step 3: Build the App

```bash
npm run build
```

Or use the build script:

```bash
./build.sh
```

## Step 4: Run the App

For development/testing:

```bash
npm start
```

The app should launch with:
- Menu bar icon visible
- Tray menu accessible
- Quick Chat window opens with `Cmd+Shift+J`

## Step 5: Verify Functionality

Test the following:

1. **Menu Bar Icon**: Look for JARVIS icon in menu bar (should be red/disconnected initially)
2. **Connection**: Icon should turn green when WebSocket connects
3. **Quick Chat**: Press `Cmd+Shift+J` to open chat window
4. **Send Message**: Type a message and press Enter
5. **Tray Menu**: Click icon to see menu options
6. **Dashboard**: Select "Open Dashboard" to verify browser opens

## Troubleshooting

### Dependencies fail to install

If you get errors during `npm install`:

```bash
# Update npm
npm install -g npm@latest

# Clear cache and retry
npm cache clean --force
npm install
```

### Build fails

```bash
# Clean and rebuild
npm run clean
rm -rf node_modules
npm install
npm run build
```

### App won't connect to server

Check that the JARVIS backend is running:

```bash
curl http://192.168.10.100:3939
```

Check WebSocket endpoint:

```bash
# Install wscat if needed
npm install -g wscat

# Test WebSocket
wscat -c ws://192.168.10.100:3939/ws
```

### Can't see menu bar icon

The icon uses a programmatically generated SVG. If you don't see it:

1. Check Console.app for errors
2. Try restarting the app
3. Check Display settings (menu bar should be visible)

## Building for Distribution

To create a macOS .app bundle and .dmg installer:

```bash
npm run dist
```

The distributable will be in `build/JARVIS-1.0.0.dmg`

## Auto-start on Login (Optional)

To make JARVIS start automatically on macOS login:

1. Build the app: `npm run dist`
2. Copy the .app from `build/mac/JARVIS.app` to `/Applications/`
3. Open System Preferences > Users & Groups > Login Items
4. Click + and add JARVIS.app

## Development Setup

For active development:

```bash
# Terminal 1: Watch TypeScript files
npm run watch

# Terminal 2: Run the app (restart after changes)
npm start
```

## Next Steps

Once verified working:

1. Test all WebSocket events (doorbell, motion, alerts)
2. Configure auto-start if desired
3. Customize settings in `src/main/config.ts`
4. Build distributable for deployment to other Macs

## Files Created

```
/opt/jarvis-v3/menubar/
├── package.json                 # Project dependencies
├── tsconfig.json                # TypeScript configuration
├── build.sh                     # Build script
├── README.md                    # Full documentation
└── src/
    ├── main/
    │   ├── index.ts            # Main process
    │   ├── config.ts           # Configuration
    │   ├── websocket.ts        # WebSocket client
    │   ├── tray.ts             # System tray
    │   └── shortcuts.ts        # Global shortcuts
    └── renderer/
        ├── preload.js          # IPC bridge
        ├── quickchat.html      # Chat UI
        └── quickchat.js        # Chat logic
```

## Support

For detailed documentation, see README.md in the project directory.
