#!/usr/bin/env python3
"""
Quick start script for Team Evaluation Assistant
"""

import subprocess
import sys
import os


def main():
    """Start the Team Evaluation Assistant"""
    print("🚀 Starting Team Evaluation Assistant...")
    print("📍 Server will be available at: http://127.0.0.1:8000")
    print("🔄 Press Ctrl+C to stop the server")
    print("-" * 50)

    try:
        # Start uvicorn server
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app:app",
            "--reload",
            "--host", "127.0.0.1",
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you're in the project directory")
        print("2. Check that dependencies are installed: uv sync")
        print("3. Verify app.py exists in the current directory")


if __name__ == "__main__":
    main()