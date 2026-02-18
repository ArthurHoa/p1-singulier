#!/usr/bin/env python3
"""
Point d'entrée principal de l'application P1-Singulier
"""

from controller.app_controller import AppController


def main():
    """Lance l'application"""
    app = AppController()
    app.run()


if __name__ == "__main__":
    main()
