#!/bin/bash

# Web UI Backend Start Script
# Starts the FastAPI backend server on port 8000

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  News Report Agent - Backend Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/webui/backend"

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}错误: 后端目录不存在: $BACKEND_DIR${NC}"
    exit 1
fi

# Change to backend directory
cd "$BACKEND_DIR"

echo -e "${GREEN}✓${NC} 后端目录: $BACKEND_DIR"
echo ""

# Check if requirements are installed
echo -e "${BLUE}检查依赖...${NC}"
if ! uv run python -c "import fastapi, uvicorn, sse_starlette" 2>/dev/null; then
    echo -e "${BLUE}安装依赖...${NC}"
    cd "$SCRIPT_DIR"
    uv pip install fastapi uvicorn sse-starlette python-multipart
    cd "$BACKEND_DIR"
fi

echo -e "${GREEN}✓${NC} 依赖已安装"
echo ""

# Start the server
echo -e "${GREEN}启动后端服务器...${NC}"
echo -e "${BLUE}地址: http://localhost:8000${NC}"
echo -e "${BLUE}API文档: http://localhost:8000/docs${NC}"
echo ""
echo -e "${BLUE}按 Ctrl+C 停止服务器${NC}"
echo ""

cd "$SCRIPT_DIR"
uv run uvicorn webui.backend.main:app --reload --port 8000 --host 0.0.0.0
