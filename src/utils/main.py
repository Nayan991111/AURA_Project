import sys
import os
import customtkinter as ctk

# 1. Add Project Root to Path
# This ensures Python finds 'src' no matter where you run this file from.
# We go up two levels: utils -> src -> AURA_PROJECT
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)

# Now we can import from src
try:
    from src.ui.app import AuraApp
except ImportError as e:
    print("❌ CRITICAL IMPORT ERROR: Could not find src.ui.app")
    print(f"   Python is looking in: {sys.path}")
    print(f"   Error Details: {e}")
    sys.exit(1)

if __name__ == "__main__":
    print(f"[BOOT] Starting Project AURA Interface...")
    print(f"   Root Path detected: {project_root}")
    
    try:
        app = AuraApp()
        app.mainloop()
    except Exception as e:
        print(f"[CRITICAL FAILURE] App crashed: {e}")
        # Keep terminal open if it crashes immediately
        input("Press Enter to exit...")