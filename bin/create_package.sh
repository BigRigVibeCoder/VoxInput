#!/bin/bash
set -e

# Version
VERSION="1.0"
PACKAGE_NAME="VoxInput_v${VERSION}"
BUILD_DIR="/tmp/voxinput_build"

echo "📦 Creating VoxInput Package ($PACKAGE_NAME)..."

# 1. Prepare Build Directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/$PACKAGE_NAME"

# 2. Copy Files
echo "   Copying files..."
cp install.sh "$BUILD_DIR/$PACKAGE_NAME/"
cp run.py "$BUILD_DIR/$PACKAGE_NAME/"
cp requirements.txt "$BUILD_DIR/$PACKAGE_NAME/"
cp LICENSE "$BUILD_DIR/$PACKAGE_NAME/" 2>/dev/null || true
cp README.md "$BUILD_DIR/$PACKAGE_NAME/" 2>/dev/null || true

# Copy Directories (excluding junk)
cp -r src "$BUILD_DIR/$PACKAGE_NAME/"
cp -r bin "$BUILD_DIR/$PACKAGE_NAME/"
cp -r assets "$BUILD_DIR/$PACKAGE_NAME/"

# 3. Clean up junk
echo "   Cleaning up __pycache__..."
find "$BUILD_DIR/$PACKAGE_NAME" -type d -name "__pycache__" -exec rm -rf {} +

# 4. Zip it up
echo "   Zipping..."
cd "$BUILD_DIR"
zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_NAME" > /dev/null

# 5. Move to current folder
cd - > /dev/null
mv "$BUILD_DIR/${PACKAGE_NAME}.zip" .

echo "✅ Package created: ${PACKAGE_NAME}.zip"
echo "   Size: $(du -hm ${PACKAGE_NAME}.zip | cut -f1) MB"
echo ""
echo "To install on another machine:"
echo "1. Transfer ${PACKAGE_NAME}.zip"
echo "2. Unzip it"
echo "3. Run ./install.sh"
