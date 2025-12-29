#!/bin/bash

# JARVIS Menu Bar App Startup Script

echo '========================================='
echo 'JARVIS v3 Menu Bar App'
echo '========================================='
echo ''

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo 'Installing dependencies...'
    npm install
    echo ''
fi

# Check if dist exists
if [ ! -d "dist" ]; then
    echo 'Building TypeScript...'
    npm run build
    echo ''
fi

echo 'Starting JARVIS Menu Bar App...'
echo ''
echo 'Press Cmd+Shift+J to open Quick Chat'
echo 'Click the menu bar icon for more options'
echo ''

npm start
