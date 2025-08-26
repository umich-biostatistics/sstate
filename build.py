#!/usr/bin/env python3
"""
Build script to compile sstate.py into a standalone binary using PyInstaller.
"""

import subprocess
import sys
import os
from pathlib import Path

def build_binary():
    """Build the sstate binary using PyInstaller."""
    
    # Define build parameters
    script_name = "sstate.py"
    binary_name = "sstate"
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Create a single executable
        "--name", binary_name,          # Name of the executable
        "--distpath", "./dist",         # Output directory
        "--workpath", "./build",        # Temporary build directory
        "--specpath", "./",             # Location for .spec file
        "--console",                    # Console application
        "--add-data", "requirements.txt:.", # Include requirements.txt
        script_name
    ]
    
    print(f"Building {binary_name} from {script_name}...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build completed successfully!")
        print(f"Binary created at: ./dist/{binary_name}")
        
        # Make the binary executable (on Unix systems)
        binary_path = Path(f"./dist/{binary_name}")
        if binary_path.exists():
            os.chmod(binary_path, 0o755)
            print(f"Made {binary_path} executable")
            
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def clean_build():
    """Clean build artifacts."""
    import shutil
    
    dirs_to_clean = ["build", "dist", "__pycache__"]
    files_to_clean = ["sstate.spec"]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Removed directory: {dir_name}")
    
    for file_name in files_to_clean:
        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"Removed file: {file_name}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean_build()
        print("Clean completed.")
    else:
        success = build_binary()
        if success:
            print("\n" + "="*50)
            print("BUILD SUCCESSFUL!")
            print("="*50)
            print(f"Your binary is ready at: ./dist/sstate")
            print("You can now copy it to your desired location.")
        else:
            print("\n" + "="*50)
            print("BUILD FAILED!")
            print("="*50)
            sys.exit(1)
