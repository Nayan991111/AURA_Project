import urllib.request
import json
import threading
import webbrowser
import customtkinter as ctk

class UpdaterService:
    """
    OTA UPDATER FRAMEWORK
    Checks a remote JSON file for the latest version.
    Triggers a non-blocking UI alert if an update is required.
    """
    def __init__(self, current_version="12.2"):
        self.current_version = current_version
        # POINTING DIRECTLY TO YOUR GITHUB REPO
        self.update_url = "https://raw.githubusercontent.com/Nayan991111/AURA_Project/main/version.json" 

    def check_for_updates(self, parent_window):
        """Spawns a background thread to check for updates."""
        threading.Thread(target=self._fetch_and_compare, args=(parent_window,), daemon=True).start()

    def _fetch_and_compare(self, parent_window):
        try:
            # 1. Fetch remote version data (5-second timeout to prevent ghost threads)
            req = urllib.request.Request(self.update_url, headers={'User-Agent': 'AuraUpdater/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
            
            remote_version = data.get("version")
            download_link = data.get("download_url")
            release_notes = data.get("release_notes", "Bug fixes and performance improvements.")

            # 2. Compare versions
            if self._is_newer(remote_version, self.current_version):
                # 3. Trigger UI Prompt safely on the Main Thread
                parent_window.after(0, self._show_update_dialog, parent_window, remote_version, release_notes, download_link)
        except Exception as e:
            # Silently fail if offline or URL is dead (Zero UI disruption)
            print(f"[UPDATER] OTA Check failed (Offline/Invalid URL): {e}")

    def _is_newer(self, remote, current):
        """Simple semantic float comparison (e.g., 12.2 > 12.1)."""
        try:
            return float(remote) > float(current)
        except ValueError:
            return remote != current

    def _show_update_dialog(self, parent, version, notes, link):
        """Renders the update prompt."""
        dialog = ctk.CTkToplevel(parent)
        dialog.title("AURA Update Available")
        dialog.geometry("450x260")
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)

        # Header
        ctk.CTkLabel(dialog, text="🚀 New Version Available!", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(dialog, text=f"Version {version} is out. You are currently on v{self.current_version}.", text_color="gray").pack()
        
        # Release Notes Box
        textbox = ctk.CTkTextbox(dialog, width=400, height=80, fg_color="#1E1E1E")
        textbox.pack(pady=10)
        textbox.insert("0.0", notes)
        textbox.configure(state="disabled")

        # Action Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Ignore for now", fg_color="transparent", border_width=1, 
                      border_color="gray", text_color="gray", hover_color="#333333", 
                      width=120, command=dialog.destroy).pack(side="left", padx=10)
        
        def download_update():
            webbrowser.open(link) # Redirects browser to your Drive/GitHub link
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="Download Update", fg_color="#F5A623", hover_color="#D48806", 
                      text_color="black", width=150, font=ctk.CTkFont(weight="bold"), 
                      command=download_update).pack(side="left", padx=10)