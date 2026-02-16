#!/usr/bin/env python3
"""
Video Studio Launcher (Cross-platform)

Simple launcher script that handles venv setup and launches the app.
"""

import subprocess
import sys
import os
from pathlib import Path

# Colors (works on most terminals)
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color


def print_colored(text, color):
    """Print colored text"""
    print(f"{color}{text}{NC}")


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print_colored(f"❌ Python 3.10+ required (found {version.major}.{version.minor})", RED)
        sys.exit(1)
    
    print_colored(f"✅ Python {version.major}.{version.minor}.{version.micro} found", GREEN)


def check_ffmpeg():
    """Check if FFmpeg is installed"""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        print_colored("✅ FFmpeg found", GREEN)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_colored("⚠️  FFmpeg not found", RED)
        print("Please install FFmpeg:")
        print("  macOS:   brew install ffmpeg")
        print("  Ubuntu:  sudo apt install ffmpeg")
        print("  Windows: Download from ffmpeg.org")
        print()


def setup_venv():
    """Setup virtual environment"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print_colored("📦 Creating virtual environment...", BLUE)
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    
    # Get python executable in venv
    if sys.platform == "win32":
        python_venv = venv_path / "Scripts" / "python.exe"
    else:
        python_venv = venv_path / "bin" / "python"
    
    return python_venv


def install_dependencies(python_venv):
    """Install dependencies"""
    print_colored("📦 Checking dependencies...", BLUE)
    subprocess.run(
        [str(python_venv), "-m", "pip", "install", "-q", "-r", "requirements.txt"],
        check=True
    )


def launch_app(python_venv):
    """Launch Video Studio"""
    print_colored("🚀 Launching Video Studio...", GREEN)
    print()
    
    # Launch as module (recommended)
    subprocess.run([str(python_venv), "-m", "src.main"])


def main():
    """Main launcher function"""
    print_colored("🎬 Video Studio Launcher", BLUE)
    print()
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Checks
    check_python_version()
    check_ffmpeg()
    
    # Setup
    python_venv = setup_venv()
    install_dependencies(python_venv)
    
    # Launch
    launch_app(python_venv)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_colored("⏹️  Cancelled", RED)
        sys.exit(0)
    except Exception as e:
        print()
        print_colored(f"❌ Error: {e}", RED)
        sys.exit(1)
