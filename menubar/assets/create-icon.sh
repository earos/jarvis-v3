#!/bin/bash
# This script creates a simple JARVIS icon using ImageMagick
# If ImageMagick is not available, you'll need to provide your own icon

if command -v convert &> /dev/null; then
    # Create a 512x512 icon with JARVIS text
    convert -size 512x512 xc:none         -fill '#667eea'         -draw 'circle 256,256 256,50'         -fill white         -font 'Helvetica-Bold'         -pointsize 120         -gravity center         -annotate +0+0 'J'         tray-icon.png
    
    echo 'Icon created: tray-icon.png'
else
    echo 'ImageMagick not found. Please provide your own tray-icon.png file.'
    echo 'Creating a placeholder file...'
    # Create a minimal 1x1 PNG as placeholder
    echo 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' | base64 -d > tray-icon.png
fi
