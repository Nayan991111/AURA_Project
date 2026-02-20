import customtkinter as ctk
from src.services.profile_manager import ProfileManager

class OnboardingView(ctk.CTkFrame):
    def __init__(self, master, on_success, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_success = on_success
        self.profile_manager = ProfileManager()

        self._build_ui()

    def _build_ui(self):
        # Center Box
        self.card = ctk.CTkFrame(self, width=500, corner_radius=15)
        self.card.place(relx=0.5, rely=0.5, anchor="center")

        # Header
        self.title_lbl = ctk.CTkLabel(self.card, text="Welcome to AURA", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_lbl.pack(pady=(30, 10))
        
        self.sub_lbl = ctk.CTkLabel(self.card, text="Please register your device to continue.", text_color="gray")
        self.sub_lbl.pack(pady=(0, 20))

        # Inputs
        self.first_name_entry = ctk.CTkEntry(self.card, placeholder_text="First Name", width=300, height=40)
        self.first_name_entry.pack(pady=10)

        self.last_name_entry = ctk.CTkEntry(self.card, placeholder_text="Last Name", width=300, height=40)
        self.last_name_entry.pack(pady=10)

        self.email_entry = ctk.CTkEntry(self.card, placeholder_text="InAmigos Email Address", width=300, height=40)
        self.email_entry.pack(pady=10)

        self.designation_entry = ctk.CTkEntry(self.card, placeholder_text="Designation (e.g., HR Manager)", width=300, height=40)
        self.designation_entry.pack(pady=10)

        # Error Label
        self.error_lbl = ctk.CTkLabel(self.card, text="", text_color="#E74C3C")
        self.error_lbl.pack(pady=(5, 0))

        # Submit Button
        self.submit_btn = ctk.CTkButton(self.card, text="REGISTER DEVICE", command=self.handle_registration, width=300, height=45, font=ctk.CTkFont(weight="bold"))
        self.submit_btn.pack(pady=(15, 30))

    def handle_registration(self):
        f_name = self.first_name_entry.get().strip()
        l_name = self.last_name_entry.get().strip()
        email = self.email_entry.get().strip()
        designation = self.designation_entry.get().strip()

        if not all([f_name, l_name, email, designation]):
            self.error_lbl.configure(text="All fields are required.")
            return

        if "@" not in email:
            self.error_lbl.configure(text="Please enter a valid email address.")
            return

        # Save to ~/.aura/profile.json
        self.profile_manager.save_profile(f_name, l_name, email, designation)
        
        # Trigger the callback to switch to Dashboard
        self.on_success()