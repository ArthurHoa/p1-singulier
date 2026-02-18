"""
Panel latéral avec informations et logs
"""

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING
from datetime import datetime
from tkcalendar import DateEntry

if TYPE_CHECKING:
    from controller.app_controller import AppController


class InfoPanel(tk.Frame):
    """Panel latéral avec informations et logs"""
    
    def __init__(self, parent, controller: 'AppController'):
        super().__init__(parent, bg="white", relief=tk.SUNKEN, borderwidth=1)
        
        self.controller = controller
        
        # Liste des logs système (en mémoire uniquement)
        self.system_logs = []  # Liste de tuples (datetime, message)
        
        # Titre
        title = tk.Label(
            self,
            text="Contrôle",
            font=("Arial", 16, "bold"),
            bg="white",
            fg="#333333"
        )
        title.pack(pady=10, padx=10, anchor="w")
        
        # Séparateur
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=5)
        
        # Frame pour les boutons (grille 2 colonnes x 3 lignes)
        buttons_frame = tk.Frame(self, bg="white")
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Configuration de la grille pour les boutons
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)
        
        # Définition des boutons
        buttons_config = [
            ("Ouvrir toutes\nles cases", self.on_open_all_boxes, 0, 0),
            ("Charger\nles P1", self.on_load_p1, 0, 1),
            ("Échanger\ndeux cases", self.on_swap_boxes, 1, 0),
            ("Ouvrir\nune case", self.on_open_single_box, 1, 1),
            ("Supprimer", self.on_delete_box, 2, 0),
            ("Affecter", self.on_assign_user, 2, 1),
        ]
        
        self.buttons = {}
        self.swap_button = None
        self.open_single_button = None
        self.delete_button = None
        self.assign_button = None
        self._swap_button_text = "Échanger\ndeux cases"
        self._open_single_button_text = "Ouvrir\nune case"
        self._delete_button_text = "Supprimer"
        self._assign_button_text = "Affecter"
        self._swap_button_bg = None
        self._swap_button_active_bg = None
        self._open_single_button_bg = None
        self._open_single_button_active_bg = None
        self._delete_button_bg = None
        self._delete_button_active_bg = None
        self._assign_button_bg = None
        self._assign_button_active_bg = None
        for label_text, command, row, col in buttons_config:
            btn = tk.Button(
                buttons_frame,
                text=label_text,
                command=command,
                font=("Arial", 10, "bold"),
                bg="#2196F3",
                fg="white",
                activebackground="#1976D2",
                activeforeground="white",
                relief=tk.RAISED,
                borderwidth=2,
                padx=5,
                pady=8,
                cursor="hand2"
            )
            btn.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            self.buttons[label_text] = btn
            if label_text == self._swap_button_text:
                self.swap_button = btn
                self._swap_button_bg = btn.cget("bg")
                self._swap_button_active_bg = btn.cget("activebackground")
            elif label_text == self._open_single_button_text:
                self.open_single_button = btn
                self._open_single_button_bg = btn.cget("bg")
                self._open_single_button_active_bg = btn.cget("activebackground")
            elif label_text == self._delete_button_text:
                self.delete_button = btn
                self._delete_button_bg = btn.cget("bg")
                self._delete_button_active_bg = btn.cget("activebackground")
            elif label_text == self._assign_button_text:
                self.assign_button = btn
                self._assign_button_bg = btn.cget("bg")
                self._assign_button_active_bg = btn.cget("activebackground")
        
        # Espacement vertical
        buttons_frame.grid_rowconfigure(0, weight=1)
        buttons_frame.grid_rowconfigure(1, weight=1)
        buttons_frame.grid_rowconfigure(2, weight=1)
        
        # Séparateur
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=15)
        
        # Indicateur d'état Arduino
        state_frame = tk.Frame(self, bg="white")
        state_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Pastille d'état
        pastille_frame = tk.Frame(state_frame, bg="white")
        pastille_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Cercle coloré (pastille)
        self.status_indicator = tk.Canvas(
            pastille_frame,
            width=20,
            height=20,
            bg="white",
            highlightthickness=0
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 8))
        
        # Label pour l'état Arduino
        self.arduino_status_label = tk.Label(
            pastille_frame,
            text="État Arduino: Non connecté",
            font=("Arial", 10),
            bg="white",
            fg="#666666"
        )
        self.arduino_status_label.pack(side=tk.LEFT, fill=tk.X)
        
        # Mise à jour initiale de l'indicateur
        self.set_arduino_connected(False)
        
        # Séparateur
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=15)
        
        # Frame pour la sélection de date
        date_frame = tk.Frame(self, bg="white")
        date_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            date_frame,
            text="Date:",
            font=("Arial", 10),
            bg="white",
            fg="#666666"
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        # Widget DateEntry pour sélectionner la date
        self.date_entry = DateEntry(
            date_frame,
            width=12,
            background="darkblue",
            foreground="white",
            borderwidth=2,
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day,
            font=("Arial", 10)
        )
        self.date_entry.pack(side=tk.LEFT, fill=tk.X)
        self.date_entry.bind("<<DateEntrySelected>>", self.on_date_change)
        
        # Séparateur
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=15)
        
        # Zone de logs
        tk.Label(
            self,
            text="Logs",
            font=("Arial", 12, "bold"),
            bg="white",
            fg="#555555"
        ).pack(anchor="w", padx=10, pady=(0, 5))
        
        # Frame pour le texte de logs avec scrollbar
        log_frame = tk.Frame(self, bg="white")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            log_frame,
            width=50,
            height=15,
            font=("Courier", 11),
            bg="#f5f5f5",
            fg="#333333",
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # Log initial
        self.add_log("Système initialisé")
        
        # Charger les logs de la date actuelle
        self.reload_logs()
    
    def on_open_all_boxes(self):
        """Callback pour ouvrir toutes les cases"""
        self.add_log("Ouverture de toutes les cases...")
        self.controller.send_arduino_command("a")
    
    def on_load_p1(self):
        """Callback pour charger les P1"""
        self.add_log("Chargement des P1...")
        self.controller.load_p1_to_arduino()

    def on_date_change(self, event):
        """Callback appelé quand la date change"""
        self.controller.get_commandes()
        # Recharger les logs pour la nouvelle date
        self.reload_logs()
    
    def on_swap_boxes(self):
        """Callback pour échanger deux cases"""
        self.add_log("Mode échange de deux cases activé")
        self.controller.on_swap_boxes()
    
    def on_open_single_box(self):
        """Callback pour ouvrir une seule case"""
        self.add_log("Mode ouverture d'une case activé - Cliquez sur une case")
        self.controller.on_open_single_box()

    def on_delete_box(self):
        """Callback pour supprimer une case"""
        self.add_log("Mode suppression d'une case activé - Cliquez sur une case")
        self.controller.on_delete_box()

    def on_assign_user(self):
        """Callback pour affecter un utilisateur à une case"""
        self.controller.on_assign_user()

    def set_swap_mode_active(self, active: bool):
        if not self.swap_button:
            return
        if active:
            self.swap_button.config(
                bg="#FFB300",
                activebackground="#FFA000",
                text=self._swap_button_text,
            )
        else:
            self.swap_button.config(
                bg=self._swap_button_bg,
                activebackground=self._swap_button_active_bg,
                text=self._swap_button_text,
            )

    def set_open_single_mode_active(self, active: bool):
        """Active/désactive le mode ouverture d'une case"""
        if not self.open_single_button:
            return
        if active:
            self.open_single_button.config(
                bg="#FFB300",
                activebackground="#FFA000",
                text=self._open_single_button_text,
            )
        else:
            self.open_single_button.config(
                bg=self._open_single_button_bg,
                activebackground=self._open_single_button_active_bg,
                text=self._open_single_button_text,
            )
    
    def set_delete_mode_active(self, active: bool):
        """Active/désactive le mode suppression d'une case"""
        if not self.delete_button:
            return
        if active:
            self.delete_button.config(
                bg="#FFB300",
                activebackground="#FFA000",
                text=self._delete_button_text,
            )
        else:
            self.delete_button.config(
                bg=self._delete_button_bg,
                activebackground=self._delete_button_active_bg,
                text=self._delete_button_text,
            )
    
    def set_assign_mode_active(self, active: bool):
        """Active/désactive le mode affectation d'un utilisateur"""
        if not self.assign_button:
            return
        if active:
            self.assign_button.config(
                bg="#FFB300",
                activebackground="#FFA000",
                text=self._assign_button_text,
            )
        else:
            self.assign_button.config(
                bg=self._assign_button_bg,
                activebackground=self._assign_button_active_bg,
                text=self._assign_button_text,
            )
    
    def set_swap_selection(self, box_id: int):
        if not self.swap_button:
            return
        self.swap_button.config(text=f"#{box_id + 1}")
    
    def set_delete_selection(self, box_id: int):
        """Affiche le numéro de case sélectionnée pour suppression"""
        if not self.delete_button:
            return
        self.delete_button.config(text=f"#{box_id + 1}")
    
    def on_button_placeholder(self):
        """Callback placeholder pour les boutons non définis"""
        self.add_log("Bouton non implémenté")
    
    def set_arduino_connected(self, is_connected: bool):
        """Change l'état de connexion Arduino"""
        if is_connected:
            color = "#4CAF50"  # Vert
            status_text = "Connecté"
        else:
            color = "#F44336"  # Rouge
            status_text = "Non connecté"
        
        # Mise à jour de la pastille
        self.status_indicator.delete("all")
        self.status_indicator.create_oval(2, 2, 18, 18, fill=color, outline=color)
        
        # Mise à jour du label
        self.arduino_status_label.config(text=f"État Arduino: {status_text}")
    
    def update_statistics(self):
        """Kept for compatibility but not used anymore"""
        pass
    
    def get_selected_date(self):
        """Retourne la date sélectionnée"""
        return self.date_entry.get_date()
    
    def add_log(self, message: str):
        """Ajoute un message système aux logs (en mémoire uniquement)"""
        now = datetime.now()
        self.system_logs.append((now, message))
        self.refresh_logs_display()
    
    def add_badge_logs(self, badge_logs: list[tuple[datetime, str]]):
        """
        Ajoute des logs de badges et rafraîchit l'affichage.
        
        Args:
            badge_logs: Liste de tuples (datetime, nom_client)
        """
        self.refresh_logs_display()
    
    def reload_logs(self):
        """Recharge les logs pour la date sélectionnée"""
        self.refresh_logs_display()
    
    def refresh_logs_display(self):
        """Rafraîchit l'affichage des logs triés par timestamp"""
        selected_date = self.get_selected_date()
        if selected_date is None:
            selected_date = datetime.now().date()
        
        # Charger les logs de badges depuis le fichier pour la date sélectionnée
        badge_logs = self.controller.load_logs_for_date(selected_date)
        
        # Filtrer les logs système pour la date sélectionnée
        filtered_system_logs = [
            (dt, msg) for dt, msg in self.system_logs
            if dt.date() == selected_date
        ]
        
        # Combiner et trier tous les logs par timestamp
        all_logs = []
        
        # Ajouter les logs de badges avec leur format
        for log_datetime, client_name in badge_logs:
            time_str = log_datetime.strftime("%H:%M:%S")
            formatted_msg = f"{client_name} a badgé à {time_str}"
            all_logs.append((log_datetime, formatted_msg))
        
        # Ajouter les logs système
        for log_datetime, message in filtered_system_logs:
            all_logs.append((log_datetime, message))
        
        # Trier par timestamp
        all_logs.sort(key=lambda x: x[0])
        
        # Effacer et remplir le widget de texte
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        
        for log_datetime, message in all_logs:
            timestamp = log_datetime.strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            self.log_text.insert(tk.END, log_entry)
        
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
