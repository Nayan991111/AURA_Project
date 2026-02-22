from src.services.updater_service import UpdaterService
import customtkinter as ctk
import threading
from typing import Any

from src.services.audit_manager import AuditManager
from src.services.profile_manager import ProfileManager
from src.ui.views.onboarding_view import OnboardingView

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class AuraApp(ctk.CTk):
    """
    PROJECT AURA - UI v2.0 (Day 16 Compliance Safe)
    - No string parsing for finance
    - Structured event driven metrics
    - Zero double counting
    """

    def __init__(self):
        super().__init__()

        self.title("AURA | InAmigos Foundation")
        self.geometry("1100x700")
        self.minsize(900, 600)

        self.profile_manager = ProfileManager()
        self.audit_manager = AuditManager(
            log_callback=self.log_message,
            finished_callback=self.on_audit_finished
        )

        self.is_running = False

        # Financial state stored safely here
        self._verified_total = 0.0
        self._flagged_total = 0
        self._scanned_total = 0

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.route_initial_view()

    # -----------------------
    # ROUTER
    # -----------------------

    def route_initial_view(self):
        if not self.profile_manager.is_registered():
            self.show_onboarding()
        else:
            self.show_dashboard()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_onboarding(self):
        self.clear_container()
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        onboarding = OnboardingView(self.container, on_success=self.show_dashboard)
        onboarding.grid(row=0, column=0, sticky="nsew")

    def show_dashboard(self):
        self.clear_container()

        self.container.grid_columnconfigure(0, weight=0)
        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

        UpdaterService(current_version="12.1").check_for_updates(self)

    # -----------------------
    # UI BUILD
    # -----------------------

    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self.container, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="PROJECT\nAURA",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.logo_label.pack(padx=20, pady=(20, 10))

        self.status_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="● SYSTEM READY",
            text_color="#00E676",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.status_label.pack(pady=10)

    def _build_main_area(self):
        self.main_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.link_entry = ctk.CTkEntry(self.main_frame, height=40)
        self.link_entry.pack(fill="x", pady=10)

        self.start_btn = ctk.CTkButton(
            self.main_frame,
            text="INITIATE AUDIT",
            command=self.start_audit_thread
        )
        self.start_btn.pack(pady=10)

        self.metric_verified = ctk.CTkLabel(self.main_frame, text="₹0.00", font=ctk.CTkFont(size=22, weight="bold"))
        self.metric_verified.pack(pady=5)

        self.metric_flagged = ctk.CTkLabel(self.main_frame, text="0")
        self.metric_flagged.pack(pady=5)

        self.metric_total = ctk.CTkLabel(self.main_frame, text="0")
        self.metric_total.pack(pady=5)

        self.console_log = ctk.CTkTextbox(self.main_frame, height=300)
        self.console_log.pack(fill="both", expand=True)
        self.console_log.configure(state="disabled")

    # -----------------------
    # ACTIONS
    # -----------------------

    def start_audit_thread(self):
        link = self.link_entry.get().strip()
        if not link or self.is_running:
            return

        self.is_running = True
        self.start_btn.configure(state="disabled", text="SCANNING...")
        self.status_label.configure(text="● RUNNING", text_color="#FFAB00")

        self._reset_metrics()

        threading.Thread(
            target=self._run_audit_process,
            args=(link,),
            daemon=True
        ).start()

    def _run_audit_process(self, link):
        self.audit_manager.start_audit(link)

    # -----------------------
    # LOG HANDLER (FIXED)
    # -----------------------

    def log_message(self, message: Any):
        self.after(0, self._update_log_ui, message)

    def _update_log_ui(self, message: Any):

        # -------- STRUCTURED EVENT HANDLING --------
        if isinstance(message, dict):
            event = message.get("event")

            if event == "SUCCESS":
                amt = float(message.get("amount", 0.0))
                self._verified_total += amt
                self._scanned_total += 1

            elif event in ("FAILED", "MANUAL"):
                self._flagged_total += 1
                self._scanned_total += 1

            self._refresh_metrics()
            return

        # -------- NORMAL LOG STRING --------
        self.console_log.configure(state="normal")
        self.console_log.insert("end", str(message) + "\n")
        self.console_log.see("end")
        self.console_log.configure(state="disabled")

    # -----------------------
    # METRIC SAFE UPDATE
    # -----------------------

    def _refresh_metrics(self):
        self.metric_verified.configure(text=f"₹{self._verified_total:,.2f}")
        self.metric_flagged.configure(text=str(self._flagged_total))
        self.metric_total.configure(text=str(self._scanned_total))

    def _reset_metrics(self):
        self._verified_total = 0.0
        self._flagged_total = 0
        self._scanned_total = 0
        self._refresh_metrics()

    # -----------------------
    # FINISH
    # -----------------------

    def on_audit_finished(self):
        self.after(0, self._reset_ui)

    def _reset_ui(self):
        self.is_running = False
        self.start_btn.configure(state="normal", text="INITIATE AUDIT")
        self.status_label.configure(text="● COMPLETE", text_color="#2979FF")