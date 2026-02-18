"""
Panel contenant la grille de 28 boîtes
"""

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from controller.app_controller import AppController

from view.box_widget import BoxWidget


class GridPanel(tk.Frame):
    """Panel contenant la grille de 28 boîtes"""
    
    def __init__(self, parent, controller: 'AppController'):
        super().__init__(parent, bg="#f0f0f0")
        
        self.controller = controller
        self.box_widgets = []
        
        # Création de la grille 4x7
        self.grid_frame = tk.Frame(self, bg="#f0f0f0")
        self.grid_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # Configuration de la grille pour qu'elle soit centrée et responsive
        for i in range(7):
            self.grid_frame.grid_rowconfigure(i, weight=1, uniform="row")
        for j in range(4):
            self.grid_frame.grid_columnconfigure(j, weight=1, uniform="col")
        
        # Création des 28 boîtes (4 colonnes x 7 lignes)
        for i in range(7):
            for j in range(4):
                box_id = i * 4 + j
                box = BoxWidget(self.grid_frame, box_id, controller)
                box.grid(row=i, column=j, sticky="nsew", padx=3, pady=3)
                self.box_widgets.append(box)
    
    def update_boxes(self):
        """Met à jour l'affichage de toutes les boîtes"""
        model = self.controller.get_model()
        for widget in self.box_widgets:
            box = model.get_box(widget.box_id)
            if box:
                widget.update_status(box)
