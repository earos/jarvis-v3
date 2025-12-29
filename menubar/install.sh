#!/bin/bash

echo '========================================='
echo 'JARVIS Menu Bar App - Installation'
echo '========================================='
echo ''

# Function to print section headers
section() {
    echo ''
    echo "--- $1 ---"
    echo ''
}

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo 'Error: package.json not found'
    echo 'Please run this script from the menubar directory'
    exit 1
fi

section 'Step 1: Installing Dependencies'
npm install

if [ $? -ne 0 ]; then
    echo ''
    echo 'Error: npm install failed'
    exit 1
fi

section 'Step 2: Building TypeScript'
npm run build

if [ $? -ne 0 ]; then
    echo ''
    echo 'Error: Build failed'
    exit 1
fi

section 'Step 3: Verification'
./verify-installation.sh

if [ $? -eq 0 ]; then
    echo ''
    echo '========================================='
    echo '✓ Installation Complete!'
    echo '========================================='
    echo ''
    echo 'To start JARVIS Menu Bar:'
    echo '  npm start'
    echo '  or'
    echo '  ./start.sh'
    echo ''
    echo 'To test without backend:'
    echo '  Terminal 1: node test-websocket.js'
    echo '  Terminal 2: npm start'
    echo ''
    echo 'Keyboard shortcuts:'
    echo '  Cmd+Shift+J - Toggle Quick Chat'
    echo '  Cmd+Q       - Quit JARVIS'
    echo ''
else
    echo ''
    echo 'Installation completed with warnings.'
    echo 'Review the verification output above.'
    echo ''
fi
