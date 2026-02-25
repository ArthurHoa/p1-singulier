"""
Widget représentant une boîte individuelle
"""

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from controller.app_controller import AppController

from model.bread_box_model import Box, BoxStatus


class BoxWidget(tk.Frame):
    """Widget représentant une boîte individuelle"""
    
    # Couleurs pour les différents états
    COLORS = {
        BoxStatus.EMPTY: "#4CAF50",      # Vert - Disponible
        BoxStatus.LOADED: "#2196F3",     # Bleu - Chargée, en attente
        BoxStatus.RETRIEVED: "#2A6B2C",  # Vert - Récupérée par client
        BoxStatus.OCCUPIED: "#BB7000",   # Orange - Récupérée (non utilisé)
        BoxStatus.RESERVED: "#BDBDBD",   # Gris - Réservée
        BoxStatus.ERROR: "#9E9E9E",      # Gris - Erreur
    }
    
    HOVER_COLORS = {
        BoxStatus.EMPTY: "#45a049",
        BoxStatus.LOADED: "#1976D2",
        BoxStatus.RETRIEVED: "#388E3C",  # Vert foncé au hover
        BoxStatus.OCCUPIED: "#BD4403",   # Orange (non utilisé)
        BoxStatus.RESERVED: "#BDBDBD",
        BoxStatus.ERROR: "#757575",
    }
    
    def __init__(self, parent, box_id: int, controller: 'AppController'):
        super().__init__(parent, relief=tk.RAISED, borderwidth=2)
        
        self.box_id = box_id
        self.controller = controller
        self.current_color = self.COLORS[BoxStatus.EMPTY]
        self.is_clickable = True
        
        # Configuration du widget
        self.configure(bg=self.current_color, cursor="hand2")
        
        # Label avec le numéro de la boîte
        self.label = tk.Label(
            self,
            text=f"#{box_id + 1}",
            font=("Arial", 12, "bold"),
            bg=self.current_color,
            fg="white"
        )
        self.label.pack(expand=True, fill=tk.BOTH)
        
        # Bindings pour l'interactivité
        self.bind("<Button-1>", self.on_click)
        self.label.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
    
    def on_click(self, event):
        """Gère le clic sur la boîte"""
        if not self.is_clickable:
            return
        self.controller.on_box_clicked(self.box_id)
    
    def on_enter(self, event):
        """Effet hover"""
        if not self.is_clickable:
            return
        box = self.controller.get_model().get_box(self.box_id)
        if box:
            hover_color = self.HOVER_COLORS[box.status]
            self.configure(bg=hover_color)
            self.label.configure(bg=hover_color)
    
    def on_leave(self, event):
        """Fin effet hover"""
        self.configure(bg=self.current_color)
        self.label.configure(bg=self.current_color)
    
    def update_status(self, box: Box):
        """Met à jour l'affichage selon le statut"""
        status = box.status
        self.current_color = self.COLORS[status]
        if status == BoxStatus.RESERVED:
            self.is_clickable = False
            self.configure(cursor="")
            self.label.configure(text="Réservée", fg="#555555")
        elif status == BoxStatus.EMPTY:
            self.is_clickable = True
            self.configure(cursor="hand2")
            self.label.configure(text=f"#{self.box_id + 1}", fg="white")
        elif status == BoxStatus.LOADED:
            # Boîte chargée, en attente de récupération
            self.is_clickable = True
            self.configure(cursor="hand2")
            name = box.user_id or ""
            bread = box.bread_name or ""
            display = f"{name}\n{bread}".strip()
            self.label.configure(text=display, fg="white")
        else:
            # OCCUPIED: Récupérée ou avec infos
            name = box.user_id or ""
            bread = box.bread_name or ""
            display = f"{name}\n{bread}".strip()
            self.is_clickable = True
            self.configure(cursor="hand2")
            self.label.configure(text=display, fg="white")
        self.configure(bg=self.current_color)
        self.label.configure(bg=self.current_color)
