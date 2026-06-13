#!/usr/bin/env python
"""
Simple test runner script for the Deepfake Detection Service.
Run this file to execute all tests with proper output formatting.
"""

import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run all tests with pytest."""
    print("=" * 70)
    print("🧪 Deepfake Detection Service - Test Suite")
    print("=" * 70)
    
    backend_dir = Path(__file__).parent
    
    # Run tests with verbose output
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "-ra"  # Show summary of all test outcomes
    ]
    
    print(f"\n📝 Running command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=backend_dir)
    
    print("\n" + "=" * 70)
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed. See output above for details.")
    print("=" * 70)
    
    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
