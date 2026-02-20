from src.services.updater_service import UpdaterService
import customtkinter as ctk
import threading
import re
from typing import Any

# Core Services
from src.services.audit_manager import AuditManager
from src.services.profile_manager import ProfileManager

# Views
from src.ui.views.onboarding_view import OnboardingView

# Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AuraApp(ctk.CTk):
    """
    PROJECT AURA - MAIN INTERFACE
    Standard: 1% SDE (Responsive, Async, Thread-Safe, View Router)
    """
    def __init__(self):
        super().__init__()

        # 1. Window Setup
        self.title("AURA | InAmigos Foundation")
        self.geometry("1100x700")
        self.minsize(900, 600)
        
        # 2. Logic Core Setup
        self.profile_manager = ProfileManager()
        self.audit_manager = AuditManager(
            log_callback=self.log_message, 
            finished_callback=self.on_audit_finished
        )
        self.is_running = False

        # 3. Root Container for View Routing
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        # 4. Trigger State Machine
        self.route_initial_view()

    # --- ROUTER LOGIC ---

    def route_initial_view(self):
        """State Machine: Decide which screen to show on boot."""
        if not self.profile_manager.is_registered():
            self.show_onboarding()
        else:
            self.show_dashboard()

    def clear_container(self):
        """Wipes the current view from the screen."""
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_onboarding(self):
        """Renders the First-Launch Registration Screen."""
        self.clear_container()
        
        # Configure container for a single centered view
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_columnconfigure(1, weight=0)
        self.container.grid_rowconfigure(0, weight=1)
        
        # Pass `self.show_dashboard` as the success callback
        onboarding = OnboardingView(self.container, on_success=self.show_dashboard)
        onboarding.grid(row=0, column=0, sticky="nsew")

    def show_dashboard(self):
        """Renders the Main Audit Interface."""
        self.clear_container()
        
        # Setup Grid Layout (2 Columns: Sidebar, Main Area)
        self.container.grid_columnconfigure(0, weight=0) # Sidebar
        self.container.grid_columnconfigure(1, weight=1) # Main Dashboard
        self.container.grid_rowconfigure(0, weight=1)
        
        self._build_sidebar()
        self._build_main_area()

        # --- NEW: TRIGGER OTA UPDATER ---
        # Fires silently in the background after the UI loads
        UpdaterService(current_version="12.1").check_for_updates(self)

    # --- DASHBOARD UI BUILDERS ---

    def _build_sidebar(self):
        """The Left Control Panel"""
        # Note: Parent is now self.container
        self.sidebar_frame = ctk.CTkFrame(self.container, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Branding
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="PROJECT\nAURA", 
                                       font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.version_label = ctk.CTkLabel(self.sidebar_frame, text="v12.1 (Stable)", 
                                          text_color="gray")
        self.version_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Status Badge
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="● SYSTEM READY", 
                                         text_color="#00E676", font=ctk.CTkFont(size=12, weight="bold"))
        self.status_label.grid(row=2, column=0, padx=20, pady=10)

    def _build_main_area(self):
        """The Right Execution Dashboard"""
        # Note: Parent is now self.container
        self.main_frame = ctk.CTkFrame(self.container, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(2, weight=1) # Log expands
        self.main_frame.grid_columnconfigure(0, weight=1)

        # A. Input Section
        self.input_frame = ctk.CTkFrame(self.main_frame)
        self.input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        self.link_label = ctk.CTkLabel(self.input_frame, text="Google Drive Folder Link:")
        self.link_label.pack(side="top", anchor="w", padx=15, pady=(10, 0))
        
        self.link_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Paste link here...", height=40)
        self.link_entry.pack(side="left", fill="x", expand=True, padx=(15, 10), pady=10)
        
        self.start_btn = ctk.CTkButton(self.input_frame, text="INITIATE AUDIT", 
                                       command=self.start_audit_thread,
                                       height=40, font=ctk.CTkFont(weight="bold"))
        self.start_btn.pack(side="right", padx=(0, 15), pady=10)

        # B. Metrics Dashboard
        self.metrics_frame = ctk.CTkFrame(self.main_frame, height=100)
        self.metrics_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        
        self.metric_verified = self._create_metric_card(self.metrics_frame, "Verified Amount", "₹0.00", 0)
        self.metric_flagged = self._create_metric_card(self.metrics_frame, "Flagged Items", "0", 1)
        self.metric_total = self._create_metric_card(self.metrics_frame, "Total Scanned", "0", 2)

        # C. The Terminal (Live Log)
        self.log_label = ctk.CTkLabel(self.main_frame, text="Execution Log (Real-Time):")
        self.log_label.grid(row=2, column=0, sticky="w", pady=(0, 5))

        self.console_log = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(family="Courier", size=13))
        self.console_log.grid(row=3, column=0, sticky="nsew")
        self.console_log.configure(state="disabled") # Read-only by default

    def _create_metric_card(self, parent, title, value, col_idx):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", expand=True, fill="x", padx=10, pady=10)
        
        title_lbl = ctk.CTkLabel(frame, text=title.upper(), font=ctk.CTkFont(size=11))
        title_lbl.pack()
        
        value_lbl = ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=22, weight="bold"))
        value_lbl.pack()
        return value_lbl

    # --- ACTION HANDLERS ---

    def start_audit_thread(self):
        """The Trigger"""
        link = self.link_entry.get().strip()
        if not link:
            self.log_message("❌ ERROR: Please enter a valid Google Drive Link.")
            return

        if self.is_running:
            return

        # UI State: Locked
        self.is_running = True
        self.start_btn.configure(state="disabled", text="SCANNING...")
        self.status_label.configure(text="● RUNNING", text_color="#FFAB00") # Amber
        self.console_log.configure(state="normal")
        self.console_log.delete("1.0", "end")
        self.console_log.configure(state="disabled")

        # Reset Metrics
        self.metric_verified.configure(text="₹0.00")
        self.metric_flagged.configure(text="0")
        self.metric_total.configure(text="0")

        # Launch Background Thread
        threading.Thread(target=self._run_audit_process, args=(link,), daemon=True).start()

    def _run_audit_process(self, link):
        """Bridge to the Controller"""
        self.audit_manager.start_audit(link)

    def log_message(self, message):
        """Thread-Safe Logging."""
        self.after(0, self._update_log_ui, message)

    def _update_log_ui(self, message):
        self.console_log.configure(state="normal")
        self.console_log.insert("end", message + "\n")
        self.console_log.see("end") 
        self.console_log.configure(state="disabled")

        # 1. Update Verified Amount
        if "[OK]" in message and "Verified" in message:
            try:
                match = re.search(r'₹\s*([\d,]+\.?\d*)', message)
                if match:
                    amt = float(match.group(1).replace(',', ''))
                    current_str = self.metric_verified.cget("text").replace("₹","").replace(",","")
                    new_total = float(current_str) + amt
                    self.metric_verified.configure(text=f"₹{new_total:,.2f}")
                    
                    current_count = int(self.metric_total.cget("text"))
                    self.metric_total.configure(text=str(current_count + 1))
            except Exception as e:
                print(f"UI Update Error: {e}")
        
        # 2. Update Flagged/Failed
        elif "[FAIL]" in message or "DUPLICATE" in message:
             current_flag = int(self.metric_flagged.cget("text"))
             self.metric_flagged.configure(text=str(current_flag + 1))
             
             current_count = int(self.metric_total.cget("text"))
             self.metric_total.configure(text=str(current_count + 1))

    def on_audit_finished(self):
        """Called when AuditManager completes"""
        self.after(0, self._reset_ui)

    def _reset_ui(self):
        self.is_running = False
        self.start_btn.configure(state="normal", text="INITIATE AUDIT")
        self.status_label.configure(text="● COMPLETE", text_color="#2979FF")
        self.log_message("-" * 40)
        self.log_message("✅ AUDIT CYCLE COMPLETED.")