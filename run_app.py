"""
Script to run the Streamlit app with proper Python path setup.
"""
import os
import sys
import subprocess

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    app_path = os.path.join(project_root, "src", "app.py")
    subprocess.run(["streamlit", "run", app_path])
