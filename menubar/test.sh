#!/bin/bash

# JARVIS Menu Bar App - Test Script
# This script performs basic checks before running the app

set -e

echo "JARVIS Menu Bar App - Pre-flight Checks"
echo "========================================"
echo ""

# Check Node.js
echo "Checking Node.js..."
if ! command -v node &> /dev/null; then
  echo "ERROR: Node.js is not installed"
  echo "Please install Node.js 18+ from https://nodejs.org/"
  exit 1
fi

NODE_VERSION=$(node -v | cut -d'.' -f1 | sed 's/v//')
if [ "$NODE_VERSION" -lt 18 ]; then
  echo "ERROR: Node.js version is too old (found v$(node -v), need v18+)"
  exit 1
fi
echo "  Node.js version: $(node -v) ✓"

# Check npm
echo "Checking npm..."
if ! command -v npm &> /dev/null; then
  echo "ERROR: npm is not installed"
  exit 1
fi
echo "  npm version: $(npm -v) ✓"

# Check if we're in the right directory
echo ""
echo "Checking project files..."
if [ ! -f "package.json" ]; then
  echo "ERROR: package.json not found"
  echo "Please run this script from the menubar directory"
  exit 1
fi
echo "  package.json ✓"

if [ ! -f "tsconfig.json" ]; then
  echo "ERROR: tsconfig.json not found"
  exit 1
fi
echo "  tsconfig.json ✓"

# Check source files
if [ ! -d "src/main" ] || [ ! -d "src/renderer" ]; then
  echo "ERROR: Source directories not found"
  exit 1
fi
echo "  Source directories ✓"

# Check dependencies
echo ""
echo "Checking dependencies..."
if [ ! -d "node_modules" ]; then
  echo "  Dependencies not installed. Running npm install..."
  npm install
else
  echo "  node_modules ✓"
fi

# Check if TypeScript is compiled
echo ""
echo "Checking build..."
if [ ! -d "dist" ]; then
  echo "  Build directory not found. Building now..."
  npm run build
else
  echo "  dist directory ✓"
fi

# Test server connectivity
echo ""
echo "Checking JARVIS server connectivity..."
if curl -s --max-time 5 http://192.168.10.100:3939 > /dev/null 2>&1; then
  echo "  HTTP server reachable ✓"
else
  echo "  WARNING: Cannot reach HTTP server at http://192.168.10.100:3939"
  echo "  The app will start but won't be able to connect to JARVIS"
fi

# Check WebSocket (if wscat is installed)
if command -v wscat &> /dev/null; then
  echo "Checking WebSocket connectivity..."
  if timeout 5 wscat -c ws://192.168.10.100:3939/ws --execute "exit" &> /dev/null; then
    echo "  WebSocket reachable ✓"
  else
    echo "  WARNING: Cannot reach WebSocket at ws://192.168.10.100:3939/ws"
  fi
else
  echo "  (wscat not installed, skipping WebSocket test)"
fi

echo ""
echo "========================================"
echo "All checks passed! ✓"
echo ""
echo "Ready to run the app:"
echo "  npm start"
echo ""
echo "Or watch for changes:"
echo "  npm run watch   # Terminal 1"
echo "  npm start       # Terminal 2"
