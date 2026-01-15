#!/bin/bash

# Web UI Frontend Start Script
# Starts the React development server on port 5173

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  News Report Agent - Frontend Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/webui/frontend"

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}错误: 前端目录不存在: $FRONTEND_DIR${NC}"
    exit 1
fi

# Change to frontend directory
cd "$FRONTEND_DIR"

echo -e "${GREEN}✓${NC} 前端目录: $FRONTEND_DIR"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}首次运行，正在安装依赖...${NC}"
    npm install
    echo -e "${GREEN}✓${NC} 依赖安装完成"
    echo ""
fi

# Start the dev server
echo -e "${GREEN}启动前端开发服务器...${NC}"
echo -e "${BLUE}地址: http://localhost:5173${NC}"
echo ""
echo -e "${BLUE}按 Ctrl+C 停止服务器${NC}"
echo ""

npm run dev
