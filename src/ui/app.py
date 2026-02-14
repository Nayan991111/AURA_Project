import customtkinter as ctk
import sys
import os
from src.ui.styles import *
from src.ui.views.audit_view import AuditView  # IMPORT THE NEW VIEW

class AuraApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Window Setup
        self.title("AURA | Automated Universal Reconciliation & Audit")
        self.geometry(f"{d_WINDOW_W}x{d_WINDOW_H}")
        self.minsize(900, 600)
        
        # Configure Grid Layout (Sidebar fixed, Main area expands)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 2. Theme Configuration
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        # 3. Initialize UI Components
        self.setup_sidebar()
        self.setup_main_area()
        
        # 4. Set Default View
        self.current_view = None
        self.show_view("Dashboard")

    def setup_sidebar(self):
        """Creates the left-hand navigation panel."""
        self.sidebar_frame = ctk.CTkFrame(self, width=d_SIDEBAR_W, corner_radius=0, fg_color=c_SURFACE)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1) # Spacer

        # App Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="PROJECT AURA", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.version_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="v1.0.0 (M4 Silicon)",
            text_color=c_TEXT_SECONDARY,
            font=ctk.CTkFont(size=10)
        )
        self.version_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Navigation Buttons (Saved as attributes so we can highlight them)
        self.btn_dashboard = self.create_nav_button("Dashboard", 2)
        self.btn_audit = self.create_nav_button("New Audit", 3)
        self.btn_history = self.create_nav_button("History", 4)
        
        # Status Badge
        self.status_badge = ctk.CTkButton(
            self.sidebar_frame,
            text="SYSTEM ONLINE",
            fg_color=c_SUCCESS,
            text_color="white",
            hover=False,
            height=25,
            font=ctk.CTkFont(size=10, weight="bold")
        )
        self.status_badge.grid(row=5, column=0, padx=20, pady=20, sticky="s")

    def create_nav_button(self, text, row):
        btn = ctk.CTkButton(
            self.sidebar_frame,
            text=text,
            fg_color="transparent",
            text_color=c_TEXT_PRIMARY,
            anchor="w",
            height=40,
            font=ctk.CTkFont(size=f_BUTTON_SIZE),
            hover_color="#404040",
            command=lambda: self.nav_callback(text)
        )
        btn.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        return btn

    def setup_main_area(self):
        """
        Initializes the different Views (Screens) of the application.
        Instead of one frame, we create multiple frames and hide/show them.
        """
        # Container for the main content
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color=c_BACKGROUND)
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # --- VIEW 1: DASHBOARD (Home) ---
        self.view_dashboard = ctk.CTkFrame(self.main_container, fg_color=c_BACKGROUND)
        
        # Dashboard Content (Placeholder for now)
        lbl_dash_title = ctk.CTkLabel(self.view_dashboard, text="Dashboard Overview", font=ctk.CTkFont(size=28, weight="bold"))
        lbl_dash_title.place(x=30, y=30)
        
        lbl_dash_info = ctk.CTkLabel(self.view_dashboard, text="Welcome to Project AURA.\nSelect 'New Audit' in the sidebar to begin scanning.", font=ctk.CTkFont(size=16), text_color=c_TEXT_SECONDARY, justify="left")
        lbl_dash_info.place(x=30, y=80)

        # --- VIEW 2: AUDIT (The Live Terminal) ---
        # We use the class we created in src/ui/views/audit_view.py
        self.view_audit = AuditView(self.main_container)

        # --- VIEW 3: HISTORY (Placeholder) ---
        self.view_history = ctk.CTkFrame(self.main_container, fg_color=c_BACKGROUND)
        ctk.CTkLabel(self.view_history, text="Audit History Log", font=ctk.CTkFont(size=28, weight="bold")).place(x=30, y=30)

    def nav_callback(self, btn_name):
        """Called when a sidebar button is clicked."""
        self.show_view(btn_name)

    def show_view(self, view_name):
        """Swaps the visible frame in the main area."""
        
        # 1. Hide all views
        self.view_dashboard.grid_forget()
        self.view_audit.grid_forget()
        self.view_history.grid_forget()

        # 2. Reset Button Styles (remove "Active" highlight)
        self.btn_dashboard.configure(fg_color="transparent")
        self.btn_audit.configure(fg_color="transparent")
        self.btn_history.configure(fg_color="transparent")

        # 3. Show the selected view and Highlight the button
        if view_name == "Dashboard":
            self.view_dashboard.grid(row=0, column=0, sticky="nsew")
            self.btn_dashboard.configure(fg_color="#404040")
            
        elif view_name == "New Audit":
            self.view_audit.grid(row=0, column=0, sticky="nsew")
            self.btn_audit.configure(fg_color="#404040") # Active Color
            
        elif view_name == "History":
            self.view_history.grid(row=0, column=0, sticky="nsew")
            self.btn_history.configure(fg_color="#404040")

    def run(self):
        self.mainloop()