#!/bin/bash

# Story MCP Server Startup Script
# This ensures we always use the correct virtual environment

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project directory
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Activate and run the server
echo "Starting Story MCP Server..."
echo "Using Python: $(./venv/bin/python --version)"
echo "Server will be available at: http://0.0.0.0:8082/mcp"
echo ""

exec ./venv/bin/python story_mcp_server.py
