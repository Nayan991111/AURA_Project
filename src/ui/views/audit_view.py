import customtkinter as ctk
import queue
from src.ui.styles import *
from src.services.audit_manager import AuditManager

class AuditView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=c_BACKGROUND)
        
        # Threading Helpers
        self.log_queue = queue.Queue()
        self.audit_manager = AuditManager(self.queue_log, self.on_audit_finished)
        
        self.setup_ui()
        
        # Start the UI update loop
        self.check_queue()

    def setup_ui(self):
        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Terminal takes all remaining space

        # 1. Header Section
        self.header = ctk.CTkLabel(
            self, 
            text="New Audit Session", 
            font=ctk.CTkFont(family=f_FAMILY, size=f_HEADER_SIZE, weight="bold"),
            text_color=c_TEXT_PRIMARY,
            anchor="w"
        )
        self.header.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="w")

        # 2. Input Control Panel
        self.control_frame = ctk.CTkFrame(self, fg_color=c_SURFACE)
        self.control_frame.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="ew")
        self.control_frame.grid_columnconfigure(0, weight=1)

        self.link_entry = ctk.CTkEntry(
            self.control_frame, 
            placeholder_text="Paste Google Drive Folder Link Here...",
            height=45,
            border_width=0,
            fg_color="#1E1E1E",
            text_color=c_TEXT_PRIMARY,
            font=ctk.CTkFont(size=14)
        )
        self.link_entry.grid(row=0, column=0, padx=15, pady=15, sticky="ew")

        self.btn_start = ctk.CTkButton(
            self.control_frame, 
            text="INITIALIZE AUDIT", 
            fg_color=c_ACCENT, 
            hover_color=c_ACCENT_HOVER,
            text_color="black",
            height=45,
            font=ctk.CTkFont(family=f_FAMILY, size=f_BUTTON_SIZE, weight="bold"),
            command=self.start_scan
        )
        self.btn_start.grid(row=0, column=1, padx=(0, 15), pady=15)

        # 3. Live Terminal (Console)
        self.terminal_frame = ctk.CTkFrame(self, fg_color=c_TERMINAL_BG, corner_radius=6)
        self.terminal_frame.grid(row=2, column=0, padx=30, pady=(0, 30), sticky="nsew")
        self.terminal_frame.grid_rowconfigure(0, weight=1)
        self.terminal_frame.grid_columnconfigure(0, weight=1)

        self.terminal = ctk.CTkTextbox(
            self.terminal_frame,
            fg_color=c_TERMINAL_BG,
            text_color=c_TERMINAL_TEXT,
            font=ctk.CTkFont(family=f_MONO, size=f_TERMINAL_SIZE),
            activate_scrollbars=True
        )
        self.terminal.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.terminal.insert("0.0", "AURA SYSTEM READY. WAITING FOR INPUT...\n")
        self.terminal.configure(state="disabled") # Read-only initially

    # --- Logic ---

    def start_scan(self):
        link = self.link_entry.get()
        if not link:
            self.log_to_terminal("[ERROR] No link provided.")
            return

        self.btn_start.configure(state="disabled", text="SCANNING...")
        self.link_entry.configure(state="disabled")
        
        self.terminal.configure(state="normal")
        self.terminal.delete("0.0", "end") # Clear terminal
        self.terminal.configure(state="disabled")
        
        # Start Background Thread
        self.audit_manager.start_audit(link)

    def on_audit_finished(self):
        # Re-enable UI (Must be done via queue/main thread, but CTk is lenient here)
        # Better to queue a "finished" signal, but this works for now.
        self.log_queue.put(("FINISH_SIGNAL", None))

    def queue_log(self, message):
        """Called by the background thread"""
        self.log_queue.put(("LOG", message))

    def check_queue(self):
        """Runs on Main Thread every 100ms to check for new logs"""
        try:
            while True:
                msg_type, content = self.log_queue.get_nowait()
                
                if msg_type == "LOG":
                    self.log_to_terminal(content)
                elif msg_type == "FINISH_SIGNAL":
                    self.btn_start.configure(state="normal", text="INITIALIZE AUDIT")
                    self.link_entry.configure(state="normal")
                    self.log_to_terminal("\n>>> READY FOR NEXT SESSION.")
                
        except queue.Empty:
            pass
        
        self.after(100, self.check_queue)

    def log_to_terminal(self, text):
        self.terminal.configure(state="normal")
        self.terminal.insert("end", text + "\n")
        self.terminal.see("end") # Auto-scroll to bottom
        self.terminal.configure(state="disabled")