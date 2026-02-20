import os
import json
import platform
import uuid

class ProfileManager:
    """
    Manages the local Employee Identity.
    Secured in the user's home directory alongside the OAuth token.
    """
    def __init__(self):
        # Path: ~/.aura/profile.json (Cross-Platform compatible)
        self.profile_dir = os.path.join(os.path.expanduser("~"), '.aura')
        self.profile_path = os.path.join(self.profile_dir, 'profile.json')

    def is_registered(self) -> bool:
        """Checks if the employee has completed the initial onboarding."""
        return os.path.exists(self.profile_path)

    def save_profile(self, first_name: str, last_name: str, email: str, designation: str) -> dict:
        """Saves profile data locally and generates a unique machine ID."""
        os.makedirs(self.profile_dir, exist_ok=True)
        
        profile_data = {
            "machine_id": str(uuid.uuid4()),  # For telemetry tracking
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "email": email.strip().lower(),
            "designation": designation.strip(),
            "os_environment": platform.system(),
            "version": "1.0.0"
        }

        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=4)
            
        return profile_data

    def get_profile(self) -> dict:
        """Returns the profile dict if it exists, else None."""
        if not self.is_registered():
            return None
        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Corrupted profile: {e}")
            return None