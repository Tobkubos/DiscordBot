#!/usr/bin/env python
"""
Setup script for the Deepfake Detection Service backend.

Run: python setup.py
"""

import os
import sys
import subprocess


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"📍 {description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(command, shell=True, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {description} failed")
        return False


def main():
    """Setup the development environment."""
    print("\n" + "="*60)
    print("🚀 Deepfake Detection Service - Backend Setup")
    print("="*60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python version: {sys.version}")
    
    # Determine OS for venv activation
    is_windows = sys.platform == "win32"
    venv_path = "venv"
    
    # Create virtual environment
    if not run_command(
        f"{sys.executable} -m venv {venv_path}",
        "Creating virtual environment"
    ):
        sys.exit(1)
    
    # Activate venv and install dependencies
    if is_windows:
        activate_cmd = f"{venv_path}\\Scripts\\activate && pip install -r requirements.txt"
    else:
        activate_cmd = f"source {venv_path}/bin/activate && pip install -r requirements.txt"
    
    if not run_command(activate_cmd, "Installing dependencies"):
        sys.exit(1)
    
    # Create .env file if it doesn't exist
    if not os.path.exists(".env"):
        run_command("copy .env.example .env" if is_windows else "cp .env.example .env",
                   "Creating .env file from template")
    
    print("\n" + "="*60)
    print("✅ Setup completed successfully!")
    print("="*60)
    print("\n📝 Next steps:")
    print(f"  1. Activate virtual environment:")
    if is_windows:
        print(f"     {venv_path}\\Scripts\\activate")
    else:
        print(f"     source {venv_path}/bin/activate")
    print(f"\n  2. Start the server:")
    print(f"     python main.py")
    print(f"\n  3. Visit http://127.0.0.1:8000/docs for interactive API docs")
    print(f"\n  4. Check .env file for configuration options")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
