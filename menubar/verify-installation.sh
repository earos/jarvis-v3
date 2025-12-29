#!/bin/bash

echo '========================================='
echo 'JARVIS Menu Bar App - Installation Check'
echo '========================================='
echo ''

ERRORS=0
WARNINGS=0

# Check Node.js
echo -n 'Checking Node.js... '
if command -v node &> /dev/null; then
    VERSION=$(node --version)
    echo "✓ Found $VERSION"
else
    echo '✗ NOT FOUND'
    echo '  Please install Node.js 18+'
    ERRORS=$((ERRORS + 1))
fi

# Check npm
echo -n 'Checking npm... '
if command -v npm &> /dev/null; then
    VERSION=$(npm --version)
    echo "✓ Found v$VERSION"
else
    echo '✗ NOT FOUND'
    ERRORS=$((ERRORS + 1))
fi

echo ''

# Check required files
echo 'Checking required files...'
FILES=(
    'package.json'
    'tsconfig.json'
    'src/main/index.ts'
    'src/main/tray.ts'
    'src/main/windows.ts'
    'src/main/websocket.ts'
    'src/main/shortcuts.ts'
    'src/main/notifications.ts'
    'src/preload/index.ts'
    'src/renderer/quick-chat.html'
    'src/renderer/doorbell.html'
    'src/renderer/styles.css'
)

for file in "${FILES[@]}"; do
    echo -n "  $file... "
    if [ -f "$file" ]; then
        echo '✓'
    else
        echo '✗ MISSING'
        ERRORS=$((ERRORS + 1))
    fi
done

echo ''

# Check assets
echo 'Checking assets...'
echo -n '  tray-icon.png... '
if [ -f 'assets/tray-icon.png' ]; then
    echo '✓'
else
    echo '⚠ MISSING (will use fallback)'
    WARNINGS=$((WARNINGS + 1))
fi

echo ''

# Check dependencies
echo 'Checking dependencies...'
if [ -d 'node_modules' ]; then
    echo '  ✓ node_modules directory exists'
    
    # Check specific packages
    PACKAGES=('electron' 'ws' 'typescript')
    for pkg in "${PACKAGES[@]}"; do
        echo -n "  Checking $pkg... "
        if [ -d "node_modules/$pkg" ]; then
            echo '✓'
        else
            echo '✗ NOT INSTALLED'
            ERRORS=$((ERRORS + 1))
        fi
    done
else
    echo '  ✗ node_modules not found'
    echo '    Run: npm install'
    ERRORS=$((ERRORS + 1))
fi

echo ''

# Check build output
echo 'Checking build output...'
if [ -d 'dist' ]; then
    echo '  ✓ dist directory exists'
    
    echo -n '  Checking compiled files... '
    if [ -f 'dist/main/index.js' ]; then
        echo '✓'
    else
        echo '✗ NOT BUILT'
        echo '    Run: npm run build'
        ERRORS=$((ERRORS + 1))
    fi
else
    echo '  ✗ dist directory not found'
    echo '    Run: npm run build'
    ERRORS=$((ERRORS + 1))
fi

echo ''
echo '========================================='
echo 'Summary'
echo '========================================='

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo '✓ Installation is complete and ready!'
    echo ''
    echo 'Next steps:'
    echo '  1. Run: npm start'
    echo '  2. Press Cmd+Shift+J to test'
    echo '  3. Check menu bar for JARVIS icon'
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠ Installation complete with $WARNINGS warning(s)"
    echo ''
    echo 'The app should work, but some features may be limited.'
    echo 'Review the warnings above.'
    exit 0
else
    echo "✗ Installation incomplete - $ERRORS error(s), $WARNINGS warning(s)"
    echo ''
    echo 'Please fix the errors above before running the app.'
    echo ''
    echo 'Quick fix:'
    echo '  npm install && npm run build'
    exit 1
fi
