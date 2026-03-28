#!/bin/bash
# Video Studio — Launch Script
cd "$(dirname "$0")"

GREEN='\033[0;32m'
RED='\033[0;31m'
DIM='\033[0;90m'
NC='\033[0m'

echo -e "${GREEN}Video Studio${NC}"

# Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Python 3 not found. Install Python 3.10+${NC}"
    exit 1
fi

# FFmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo -e "${RED}FFmpeg not found.${NC}"
    echo "  macOS:  brew install ffmpeg"
    echo "  Linux:  sudo apt install ffmpeg"
    exit 1
fi

# Venv
if [ ! -d "venv" ]; then
    echo -e "${DIM}Creating venv...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate

# Deps
pip install -q -r requirements.txt 2>/dev/null

# Launch
echo -e "${DIM}Starting...${NC}"
python3 -m src.main
