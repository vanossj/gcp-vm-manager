#!/bin/bash
# GCP VM Manager - GUI Launcher Script
# This script runs the GUI application directly from GitHub using uvx

# Configuration - Update this with your actual GitHub repo
GITHUB_REPO="git+https://github.com/vanossj/gcp-vm-manager.git"

echo "🔧 GCP VM Manager - GUI Launcher"
echo "================================"
echo "Running directly from GitHub repository"
echo

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV package manager not found!"
    echo "Please install UV first from: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

echo "✅ UV package manager found"
echo

# Run the GUI application directly from GitHub using uvx
echo "🚀 Launching GCP VM Manager GUI from GitHub..."
echo "Repository: $GITHUB_REPO"
echo

uvx --from "$GITHUB_REPO" gcp-vm-manager-gui

if [ $? -eq 0 ]; then
    echo "✅ Application completed successfully"
else
    echo "❌ Failed to run application"
    echo "Please check:"
    echo "  - GitHub repository URL is correct"
    echo "  - You have internet connection"
    echo "  - Repository is accessible"
    exit 1
fi
