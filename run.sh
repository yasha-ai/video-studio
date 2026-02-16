#!/bin/bash
# Video Studio Launcher Script

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎬 Video Studio Launcher${NC}"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}⚠️  FFmpeg not found.${NC}"
    echo "Please install FFmpeg:"
    echo "  macOS:   brew install ffmpeg"
    echo "  Ubuntu:  sudo apt install ffmpeg"
    echo ""
fi

# Check virtual environment
if [ ! -d "venv" ]; then
    echo -e "${BLUE}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo -e "${BLUE}📦 Checking dependencies...${NC}"
pip install -q -r requirements.txt

# Launch application
echo -e "${GREEN}🚀 Launching Video Studio...${NC}"
echo ""
python3 -m src.main

# Deactivate on exit
deactivate
