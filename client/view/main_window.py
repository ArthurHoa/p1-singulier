"""
Fenêtre principale de l'application
"""

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from controller.app_controller import AppController

from view.grid_panel import GridPanel
from view.info_panel import InfoPanel

class MainWindow:
    """Fenêtre principale de l'application"""
    
    def __init__(self, controller: 'AppController'):
        self.controller = controller
        
        # Création de la fenêtre principale
        self.root = tk.Tk()
        self.root.title("P1-Singulier - Gestion des Boîtes à Pain")
        self.root.geometry("1500x1000")
        self.root.minsize(900, 600)
        
        # Configuration du style
        self.root.configure(bg="#f0f0f0")
        
        # Frame principal avec deux colonnes
        main_container = tk.Frame(self.root, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=8) 
        main_container.grid_columnconfigure(1, weight=2)  
        
        # Panel gauche : grille de boîtes
        self.grid_panel = GridPanel(main_container, controller)
        self.grid_panel.grid(row=0, column=0, sticky="nsew")
        
        # Panel droit : informations
        self.info_panel = InfoPanel(main_container, controller)
        self.info_panel.grid(row=0, column=1, sticky="nsew")
        
        # Initialisation de l'affichage
        self.update_display()
    
    def run(self):
        """Lance la boucle principale de l'interface"""
        self.root.mainloop()
    
    def update_display(self):
        """Met à jour l'affichage complet"""
        self.grid_panel.update_boxes()
        self.info_panel.update_statistics()

    def get_selected_date(self):
        """Retourne la date sélectionnée"""
        return self.info_panel.get_selected_date()
