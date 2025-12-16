
import runpy
import os
import sys

# Ensure the project root is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        runpy.run_module('src.main', run_name='__main__', alter_sys=True)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)
