import customtkinter as ctk
import sys
import os
from src.ui.styles import *

class AuraApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Window Setup
        self.title("AURA | Automated Universal Reconciliation & Audit")
        self.geometry(f"{d_WINDOW_W}x{d_WINDOW_H}")
        self.minsize(900, 600)
        
        # Configure Grid Layout (1x2: Sidebar + Main Content)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 2. Theme Configuration
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue") # We override this with our styles anyway

        # 3. Initialize Components
        self.setup_sidebar()
        self.setup_main_area()
        
        # 4. State Management (Placeholder for Day 11)
        self.current_view = "DASHBOARD"

    def setup_sidebar(self):
        """Creates the left-hand navigation panel."""
        self.sidebar_frame = ctk.CTkFrame(self, width=d_SIDEBAR_W, corner_radius=0, fg_color=c_SURFACE)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1) # Spacer

        # App Logo / Title
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

        # Navigation Buttons
        self.btn_dashboard = self.create_nav_button("Dashboard", 2)
        self.btn_audit = self.create_nav_button("New Audit", 3)
        self.btn_history = self.create_nav_button("History", 4)
        
        # Status Badge (Bottom of Sidebar)
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
        """Creates the right-hand content area."""
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=c_BACKGROUND)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        
        # Header
        self.header_label = ctk.CTkLabel(
            self.main_frame,
            text="Dashboard",
            font=ctk.CTkFont(family=f_FAMILY, size=28, weight="bold"),
            text_color=c_TEXT_PRIMARY
        )
        self.header_label.place(x=30, y=30)
        
        # Placeholder Content
        self.info_label = ctk.CTkLabel(
            self.main_frame,
            text="Welcome to Project AURA.\nSelect 'New Audit' to begin scanning Drive folders.",
            font=ctk.CTkFont(size=16),
            text_color=c_TEXT_SECONDARY,
            justify="left"
        )
        self.info_label.place(x=30, y=80)

    def nav_callback(self, btn_name):
        print(f"[DEBUG] Navigation: {btn_name}")
        self.header_label.configure(text=btn_name)
        # Logic to swap frames will go here in Day 11

    def run(self):
        self.mainloop()