#!/bin/bash

# JARVIS Menu Bar App - Build Script
# This script builds the Electron app for macOS

set -e

echo "Building JARVIS Menu Bar App..."

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
  echo "Error: package.json not found. Please run this script from the menubar directory."
  exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
npm run clean

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Build TypeScript
echo "Compiling TypeScript..."
npm run build

# Check if build was successful
if [ ! -d "dist" ]; then
  echo "Error: TypeScript compilation failed"
  exit 1
fi

echo "Build completed successfully!"
echo ""
echo "To run the app:"
echo "  npm start"
echo ""
echo "To create distributable:"
echo "  npm run dist"
