"""
Contrôleur principal de l'application
"""

from pathlib import Path
import threading
import time
from datetime import datetime
from typing import Optional
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog

from model.bread_box_model import BreadBoxModel, BoxStatus
from model.users import Badgelist
from view.main_window import MainWindow
from controller import network_utils


class AppController:
    """Contrôleur principal coordonnant Model et View"""
    
    def __init__(self):
        # Initialise le modèle
        self.model = BreadBoxModel(num_boxes=28)
        self.badge_list = Badgelist()

        self.swap_mode = False
        self.swap_selection: list[int] = []
        
        self.open_single_mode = False
        self.delete_mode = False
        self.assign_mode = False
        self.selected_user: Optional[str] = None
        
        # Initialise la vue
        self.view = MainWindow(self)

        # Enregistre la vue comme observateur du modèle
        self.model.register_observer(self.on_model_changed)

        self._apply_reserved_box_from_config()
        
        # Thread pour la vérification Arduino
        self._arduino_check_thread = None
        self._stop_arduino_check = False
    
    def run(self):
        """Lance l'application"""
        self.view.root.after(200, self.get_commandes)
        self._start_arduino_check()
        self.view.run()
    
    def on_model_changed(self):
        """Callback appelé quand le modèle change"""
        self.view.update_display()
    
    def on_box_clicked(self, box_id: int):
        """Gère le clic sur une boîte"""
        if self.open_single_mode:
            # Envoyer la commande d'ouverture pour cette case
            command = f"o{box_id}"
            self.send_arduino_command(command)
            self.view.info_panel.add_log(f"Ouverture de la case #{box_id + 1}")
            
            # Désactiver le mode
            self.open_single_mode = False
            self.view.info_panel.set_open_single_mode_active(False)
            return
        
        if self.delete_mode:
            # Vider la case localement (client-side uniquement)
            box = self.model.get_box(box_id)
            box.set_status(BoxStatus.EMPTY, user_id=None, bread_name=None)
            self.model.notify_observers()
            self.view.info_panel.add_log(f"Suppression du contenu de la case #{box_id + 1}")
            
            # Désactiver le mode
            self.delete_mode = False
            self.view.info_panel.set_delete_mode_active(False)
            return
        
        if self.assign_mode and self.selected_user:
            # Affecter l'utilisateur à la case (client-side uniquement)
            box = self.model.get_box(box_id)
            box.set_status(BoxStatus.LOADED, user_id=self.selected_user, bread_name=None)
            self.model.notify_observers()
            self.view.info_panel.add_log(f"Affectation de {self.selected_user} à la case #{box_id + 1}")
            
            # Désactiver le mode
            self.assign_mode = False
            self.selected_user = None
            self.view.info_panel.set_assign_mode_active(False)
            return
        
        if self.swap_mode:
            if box_id not in self.swap_selection:
                self.swap_selection.append(box_id)
                if len(self.swap_selection) == 1:
                    self.view.info_panel.set_swap_selection(box_id)
            if len(self.swap_selection) == 2:
                self.model.swap_box_contents(
                    self.swap_selection[0],
                    self.swap_selection[1],
                )
                self.swap_mode = False
                self.swap_selection = []
                self.view.info_panel.set_swap_mode_active(False)
            return

        box = self.model.get_box(box_id)

    def get_commandes(self):
        selected_date = self.view.get_selected_date()
        if selected_date is None:
            return

        date_str = selected_date.strftime("%Y-%m-%d")
        
        if not self._read_debug_mode():
            network_utils.get_commandes(date_str)

        self.model.load_pains()
        
        # Synchroniser avec les logs - statut de base OCCUPIED (orange)
        self._sync_boxes_status_with_logs(base_status=BoxStatus.OCCUPIED)

    def on_swap_boxes(self):
        self.swap_mode = True
        self.swap_selection = []
        self.view.info_panel.set_swap_mode_active(True)
    
    def on_open_single_box(self):
        """Active le mode d'ouverture d'une seule case"""
        self.open_single_mode = True
        self.view.info_panel.set_open_single_mode_active(True)
    
    def on_delete_box(self):
        """Active le mode de suppression (vidage) d'une case"""
        self.delete_mode = True
        self.view.info_panel.set_delete_mode_active(True)
    
    def on_assign_user(self):
        """Affiche une popup de sélection d'utilisateurs et active le mode affectation"""
        # Récupérer les noms uniques des badges
        unique_names = sorted(list(set(
            badge.name for badge in self.badge_list.badges if badge.name
        )))
        
        if not unique_names:
            self.view.info_panel.add_log("Aucun utilisateur disponible")
            return
        
        # Créer une popup de sélection
        self._show_user_selection_popup(unique_names)
    
    def _show_user_selection_popup(self, user_names: list[str]):
        """Affiche une popup pour sélectionner un utilisateur"""
        import tkinter as tk
        
        # Créer une fenêtre Toplevel
        popup = tk.Toplevel(self.view.root)
        popup.title("Sélectionner un utilisateur")
        popup.geometry("300x400")
        popup.resizable(False, False)
        
        # Centrer la popup
        popup.transient(self.view.root)
        popup.grab_set()
        
        # Label
        label = tk.Label(popup, text="Choisir un utilisateur:", font=("Arial", 12, "bold"))
        label.pack(pady=10, padx=10)
        
        # Listbox avec scrollbar
        frame = tk.Frame(popup)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        for name in user_names:
            listbox.insert(tk.END, name)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                self.selected_user = user_names[selection[0]]
                self.assign_mode = True
                self.view.info_panel.set_assign_mode_active(True)
                self.view.info_panel.add_log(f"Mode affectation activé - Utilisateur: {self.selected_user}")
                popup.destroy()
        
        def on_cancel():
            popup.destroy()
        
        # Boutons
        button_frame = tk.Frame(popup)
        button_frame.pack(pady=10, padx=10, fill=tk.X)
        
        confirm_btn = tk.Button(button_frame, text="Valider", command=on_select, bg="#4CAF50", fg="white")
        confirm_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        cancel_btn = tk.Button(button_frame, text="Annuler", command=on_cancel, bg="#f44336", fg="white")
        cancel_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    
    def load_p1_to_arduino(self):
        """
        Charge les P1 sur l'Arduino en envoyant la commande 'c' 
        suivie des badges des clients.
        Puis met à jour les statuts des boîtes et vérifie les logs.
        """
        try:
            message = self._build_load_command()
            if message:
                self.send_arduino_command(message)
                self.view.info_panel.add_log("Commande de chargement envoyée à l'Arduino")
                
                # Mettre à jour les statuts après envoi (statut de base LOADED = bleu)
                self._sync_boxes_status_with_logs(base_status=BoxStatus.LOADED)
                self.view.info_panel.add_log("Statuts des boîtes mis à jour")
        except ValueError as e:
            # Afficher un popup d'erreur
            messagebox.showerror("Erreur", str(e))
            self.view.info_panel.add_log(f"Erreur: {e}")
    
    def _sync_boxes_status_with_logs(self, base_status: BoxStatus = BoxStatus.LOADED):
        """
        Synchronise les statuts des boîtes avec les logs de la date actuelle:
        - Si utilisateur assigné ET nom dans logs → RETRIEVED (vert)
        - Si utilisateur assigné ET nom NON dans logs → base_status (paramètre)
        - Si pas d'utilisateur → EMPTY (vert)
        
        Args:
            base_status: Statut à appliquer si utilisateur assigné mais NON dans logs
                        (BoxStatus.OCCUPIED après get_commandes, BoxStatus.LOADED après load_p1)
        """
        from datetime import date
        
        # Charger les logs de la date du date_entry (pas la date d'aujourd'hui)
        current_date = self.view.info_panel.date_entry.get_date()
        badge_logs = self.load_logs_for_date(current_date)
        
        # Créer un set des noms qui ont récupéré leur boîte
        retrieved_names = set()
        for log_datetime, client_name in badge_logs:
            retrieved_names.add(client_name.lower())
        
        # Mettre à jour les boîtes
        for i in range(self.model.num_boxes):
            box = self.model.get_box(i)
            if not box:
                continue
            
            # Si pas d'utilisateur, la boîte est vide
            if not box.user_id:
                if box.status != BoxStatus.RESERVED:
                    box.set_status(BoxStatus.EMPTY)
                continue
            
            # L'utilisateur est assigné, vérifier les logs
            user_name = box.user_id.strip().lower()
            
            if user_name in retrieved_names:
                # Le client a récupéré sa boîte → RETRIEVED (vert)
                box.set_status(BoxStatus.RETRIEVED, box.user_id, box.bread_name, retrieved=True)
            else:
                # Le client n'a pas récupéré → utiliser le statut de base
                box.set_status(base_status, box.user_id, box.bread_name, retrieved=False)
        
        # Notifier les observateurs pour mettre à jour l'affichage
        self.model.notify_observers()
    
    def _build_load_command(self) -> str:
        """
        Construit la commande de chargement pour l'Arduino.
        Format: c-BADGE1-BADGE2-00000000-BADGE3,BADGE3_2
        
        Returns:
            La commande à envoyer (sans le point final)
            
        Raises:
            ValueError: Si un nom d'utilisateur n'a pas de badge correspondant
        """
        message_parts = ["c"]
        
        # Trouver la dernière boîte non vide
        last_occupied_box = -1
        for i in range(self.model.num_boxes):
            box = self.model.get_box(i)
            if box and box.user_id:
                last_occupied_box = i
        
        # Si aucune boîte n'est occupée, envoyer juste "c"
        if last_occupied_box == -1:
            return "c"
        
        # Parcourir les boîtes jusqu'à la dernière occupée
        for i in range(last_occupied_box + 1):
            box = self.model.get_box(i)
            if not box:
                message_parts.append("00000000")
                continue
            
            if not box.user_id or not box.user_id.strip():
                # Boîte vide
                message_parts.append("00000000")
            else:
                # Chercher le(s) badge(s) pour ce nom
                user_name = box.user_id.strip()
                badges = self._find_badges_for_name(user_name)
                
                if not badges:
                    raise ValueError(f"Nom: {user_name} inconnu du fichier de badges")
                
                # Joindre les badges avec une virgule (max 2)
                badge_str = ",".join(badges[:2])
                message_parts.append(badge_str)
        
        return "-".join(message_parts)
    
    def _find_badges_for_name(self, name: str) -> list[str]:
        """
        Trouve tous les badges correspondant à un nom d'utilisateur.
        
        Args:
            name: Nom de l'utilisateur à chercher
            
        Returns:
            Liste des codes de badges (max 2)
        """
        badges = []
        for badge in self.badge_list.badges:
            if badge.name and badge.name.strip().lower() == name.lower():
                badges.append(badge.code.upper())
                if len(badges) >= 2:
                    break
        return badges


    def _apply_reserved_box_from_config(self):
        box_id = self._read_reserved_box_id()
        if box_id is None:
            return

        if not (0 <= box_id < self.model.num_boxes):
            return

        self.model.reserve_box(box_id)

    def _read_reserved_box_id(self):
        base_dir = Path(__file__).resolve().parents[2]
        config_path = base_dir / "config" / "config.txt"
        if not config_path.exists():
            return None

        raw_value = None
        with config_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip().lower()
                value = value.strip()
                if key in {"boxnumber", "boxnnumber", "boxnumer"}:
                    raw_value = value
                    break

        if raw_value is None:
            return None

        try:
            box_number = int(raw_value)
        except ValueError:
            return None

        return box_number - 1

    def _read_debug_mode(self) -> bool:
        """Lit debugMode depuis config.txt."""
        base_dir = Path(__file__).resolve().parents[2]
        config_path = base_dir / "config" / "config.txt"
        if not config_path.exists():
            return False

        with config_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip().lower() == "debugmode":
                    return value.strip().lower() == "true"
    
    def _read_arduino_config(self) -> tuple[str, int] | None:
        """Lit l'IP et le port de l'Arduino depuis config.txt."""
        base_dir = Path(__file__).resolve().parents[2]
        config_path = base_dir / "config" / "config.txt"
        if not config_path.exists():
            return None
        
        ip = None
        port = None
        
        with config_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == "ip":
                    ip = value
                elif key == "port":
                    try:
                        port = int(value)
                    except ValueError:
                        pass
        
        if ip and port:
            return (ip, port)
        return None
    
    def _check_arduino_status(self):
        """Vérifie périodiquement l'état de connexion Arduino."""
        arduino_config = self._read_arduino_config()
        if not arduino_config:
            return
        
        ip, port = arduino_config
        
        while not self._stop_arduino_check:
            is_connected = network_utils.check_arduino_connection(ip, port)
            
            # Mise à jour de l'interface dans le thread principal de Tkinter
            self.view.root.after(0, lambda connected=is_connected: 
                                self.view.info_panel.set_arduino_connected(connected))
            
            # Si Arduino est connecté, charger les logs
            if is_connected:
                self.charger_logs()
            
            # Attendre 60 secondes avant la prochaine vérification
            time.sleep(60)
    
    def _start_arduino_check(self):
        """Démarre le thread de vérification Arduino."""
        self._stop_arduino_check = False
        self._arduino_check_thread = threading.Thread(
            target=self._check_arduino_status,
            daemon=True
        )
        self._arduino_check_thread.start()
    
    def stop(self):
        """Arrête proprement l'application et les threads."""
        self._stop_arduino_check = True
        if self._arduino_check_thread:
            self._arduino_check_thread.join(timeout=1)
    
    def send_arduino_command(self, message: str):
        """
        Envoie une commande à l'Arduino de manière asynchrone.
        
        Args:
            message: Message à envoyer à l'Arduino
        """
        def _send():
            arduino_config = self._read_arduino_config()
            if not arduino_config:
                self.view.root.after(0, lambda: 
                    self.view.info_panel.add_log("Erreur: configuration Arduino introuvable"))
                return
            
            ip, port = arduino_config
            success, response = network_utils.send_arduino_command(ip, port, message)
            
            # Log dans le thread principal de Tkinter
            if not success:
                self.view.root.after(0, lambda r=response: 
                    self.view.info_panel.add_log(f"Erreur d'envoi: {r}"))
        
        # Exécuter dans un thread pour ne pas bloquer l'interface
        thread = threading.Thread(target=_send, daemon=True)
        thread.start()
        return False
    
    def charger_logs(self):
        """
        Récupère les logs de l'Arduino en envoyant la commande 'l'.
        Parse et sauvegarde les logs dans le fichier du mois courant.
        """
        arduino_config = self._read_arduino_config()
        if not arduino_config:
            print("Erreur: configuration Arduino introuvable")
            return
        
        ip, port = arduino_config
        
        # Buffer de 1 MB pour les logs (comme dans le code C#)
        success, logs_data = network_utils.send_arduino_command(
            ip, port, "l", timeout=10.0, buffer_size=1048576
        )
        
        if success:
            
            # Envoyer "r" pour indiquer à l'Arduino de supprimer les logs
            if logs_data and logs_data.strip():
                # Parser et sauvegarder les logs
                new_logs = self._parse_and_save_logs(logs_data)
                
                # Afficher les nouveaux logs dans l'interface
                if new_logs:
                    self.view.root.after(0, lambda logs=new_logs: 
                                        self.view.info_panel.add_badge_logs(logs))
                
                # Synchroniser les statuts des boîtes avec les logs
                self.view.root.after(0, self._sync_boxes_status_with_logs)
                
                reset_success, _ = network_utils.send_arduino_command(
                    ip, port, "r", timeout=5.0
                )
                if not reset_success:
                    print("Erreur lors de l'envoi de la commande de suppression")
        else:
            print(f"Erreur lors de la récupération des logs: {logs_data}")
    
    def _parse_and_save_logs(self, logs_data: str) -> list[tuple[datetime, str]]:
        """
        Parse les logs Arduino et les sauvegarde dans le fichier du mois courant.
        
        Format d'entrée: BADGE_DECIMAL;HH:MM:SS
        Format de sortie: DD/MM/YYYY HH:MM:SS;NOM_CLIENT (ou BADGE_HEX si inconnu)
        
        Retourne la liste des logs parsés avec leur timestamp complet.
        """
        if not logs_data or not logs_data.strip():
            return []
        
        # Obtenir la date/heure actuelle
        now = datetime.now()
        current_time = now.time()
        
        # Nom du fichier de log (logs_MM_YY.txt)
        base_dir = Path(__file__).resolve().parents[2]
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Parser chaque ligne de log
        parsed_logs = []
        logs_to_save = {}  # Dict[Path, list[str]] pour grouper par fichier
        
        for line in logs_data.strip().split('\n'):
            line = line.strip()
            if not line or ';' not in line:
                continue
            
            try:
                badge_decimal, time_str = line.split(';', 1)
                badge_decimal = badge_decimal.strip()
                time_str = time_str.strip()
                
                # Parser l'heure du log
                log_time = datetime.strptime(time_str, "%H:%M:%S").time()
                
                # Si l'heure du log est supérieure à l'heure actuelle, c'est hier
                if log_time > current_time:
                    # Utiliser timedelta pour reculer d'un jour
                    from datetime import timedelta
                    log_datetime = datetime.combine(now.date(), log_time) - timedelta(days=1)
                else:
                    log_datetime = datetime.combine(now.date(), log_time)
                
                date_str = log_datetime.strftime("%d/%m/%Y")
                
                # Convertir le badge décimal en hexadécimal (toujours 8 caractères)
                badge_hex = f"{int(badge_decimal):08X}"
                
                # Chercher le nom du client dans badge_list
                client_name = badge_hex  # Par défaut, on garde le badge en hexa
                for badge in self.badge_list.badges:
                    if badge.code.upper() == badge_hex:
                        if badge.name:
                            client_name = badge.name
                        break
                
                # Ajouter à la liste des logs parsés (pour l'interface)
                parsed_logs.append((log_datetime, client_name))
                
                # Préparer la ligne pour le fichier
                log_filename = f"logs_{log_datetime.strftime('%m_%y')}.txt"
                log_path = logs_dir / log_filename
                log_entry = f"{date_str} {time_str};{client_name}\n"
                
                if log_path not in logs_to_save:
                    logs_to_save[log_path] = []
                logs_to_save[log_path].append(log_entry)
                
            except (ValueError, IndexError) as e:
                print(f"Erreur lors du parsing de la ligne '{line}': {e}")
                continue
        
        # Sauvegarder dans les fichiers (mode ajout)
        total_saved = 0
        for log_path, entries in logs_to_save.items():
            with log_path.open("a", encoding="utf-8") as f:
                f.writelines(entries)
            total_saved += len(entries)
        
        return parsed_logs
    
    def get_model(self) -> BreadBoxModel:
        """Retourne le modèle"""
        return self.model
    
    def load_logs_for_date(self, date: datetime.date) -> list[tuple[datetime, str]]:
        """
        Charge les logs de badges pour une date donnée depuis le fichier.
        
        Args:
            date: Date pour laquelle charger les logs
            
        Returns:
            Liste de tuples (datetime, nom_client)
        """
        base_dir = Path(__file__).resolve().parents[2]
        logs_dir = base_dir / "logs"
        
        # Nom du fichier de log pour le mois de cette date
        log_filename = f"logs_{date.strftime('%m_%y')}.txt"
        log_path = logs_dir / log_filename
        
        if not log_path.exists():
            return []
        
        logs = []
        date_str = date.strftime("%d/%m/%Y")
        
        try:
            with log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or ';' not in line:
                        continue
                    
                    try:
                        datetime_str, client_name = line.split(';', 1)
                        # Format: DD/MM/YYYY HH:MM:SS
                        log_datetime = datetime.strptime(datetime_str.strip(), "%d/%m/%Y %H:%M:%S")
                        
                        # Ne garder que les logs de la date demandée
                        if log_datetime.date() == date:
                            logs.append((log_datetime, client_name.strip()))
                    except (ValueError, IndexError) as e:
                        print(f"Erreur lors de la lecture de la ligne '{line}': {e}")
                        continue
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier {log_path}: {e}")
        
        return logs
