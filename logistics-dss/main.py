"""
Logistics DSS - Application Entry Point
Phase 8: login gate — LoginView shown first; on success launches LogisticsDSSApp.
"""

import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ui.views.login_view import LoginView
from src.ui.app import LogisticsDSSApp


def main():
    def on_login_success(user):
        app = LogisticsDSSApp(current_user=user)
        app.mainloop()

    login = LoginView(on_success=on_login_success)
    login.mainloop()


if __name__ == "__main__":
    main()
