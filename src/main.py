import sys
import os

# Ensure the project root is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ui.app import AuraApp

if __name__ == "__main__":
    print("[BOOT] Initializing Project AURA GUI Environment...")
    app = AuraApp()
    app.run()