"""
Modèle de données pour les boîtes à pain
"""

from enum import Enum
from typing import List, Optional
from datetime import datetime
from pathlib import Path


class BoxStatus(Enum):
    """États possibles d'une boîte"""
    EMPTY = "empty"           # Vide
    LOADED = "loaded"         # Chargée, en attente de récupération
    RETRIEVED = "retrieved"   # Récupérée par le client
    OCCUPIED = "occupied"     # Statut hérité (non utilisé actuellement)
    RESERVED = "reserved"     # Réservée
    ERROR = "error"           # Erreur


class Box:
    """Représente une boîte à pain"""
    
    def __init__(self, box_id: int, size: int = 1):
        self.id = box_id
        self.size = size
        self.status = BoxStatus.EMPTY
        self.user_id: Optional[str] = None
        self.bread_name: Optional[str] = None
        self.timestamp: Optional[datetime] = None
        self.retrieved: bool = False  # Indique si la boîte a été récupérée
    
    def set_status(
        self,
        status: BoxStatus,
        user_id: Optional[str] = None,
        bread_name: Optional[str] = None,
        retrieved: bool = False,
    ):
        """Change le statut de la boîte"""
        self.status = status
        self.user_id = user_id
        self.retrieved = retrieved
        if status == BoxStatus.EMPTY:
            self.bread_name = None
        elif bread_name is not None:
            self.bread_name = bread_name
        self.timestamp = datetime.now()
    
    def is_available(self) -> bool:
        """Vérifie si la boîte est disponible"""
        return self.status == BoxStatus.EMPTY


class BreadBoxModel:
    """Modèle principal gérant les 28 boîtes"""
    
    def __init__(self, num_boxes: int = 28):
        self.num_boxes = num_boxes
        sizes = self._read_box_sizes(num_boxes)
        self.boxes: List[Box] = [Box(i, sizes[i]) for i in range(num_boxes)]
        self._observers = []
    
    def register_observer(self, callback):
        """Enregistre un observateur pour les changements"""
        self._observers.append(callback)
    
    def notify_observers(self):
        """Notifie tous les observateurs des changements"""
        for callback in self._observers:
            callback()
    
    def get_box(self, box_id: int) -> Optional[Box]:
        """Récupère une boîte par son ID"""
        if 0 <= box_id < self.num_boxes:
            return self.boxes[box_id]
        return None
    
    def update_box_status(self, box_id: int, status: BoxStatus, user_id: Optional[str] = None):
        """Met à jour le statut d'une boîte"""
        box = self.get_box(box_id)
        if box:
            box.set_status(status, user_id)
            self.notify_observers()

    def reserve_box(self, box_id: int):
        """Passe une boîte en statut réservé"""
        self.update_box_status(box_id, BoxStatus.RESERVED)
    
    def get_available_boxes(self) -> List[Box]:
        """Retourne la liste des boîtes disponibles"""
        return [box for box in self.boxes if box.is_available()]
    
    def get_statistics(self) -> dict:
        """Retourne des statistiques sur les boîtes"""
        stats = {
            'total': self.num_boxes,
            'empty': 0,
            'occupied': 0,
            'reserved': 0,
            'error': 0
        }
        for box in self.boxes:
            stats[box.status.value] += 1
        return stats

    def swap_box_contents(self, box_id_a: int, box_id_b: int) -> bool:
        """Intervertit le contenu de deux boîtes (sans changer leur id/size)."""
        if box_id_a == box_id_b:
            return False
        box_a = self.get_box(box_id_a)
        box_b = self.get_box(box_id_b)
        if not box_a or not box_b:
            return False

        box_a.status, box_b.status = box_b.status, box_a.status
        box_a.user_id, box_b.user_id = box_b.user_id, box_a.user_id
        box_a.bread_name, box_b.bread_name = box_b.bread_name, box_a.bread_name
        box_a.timestamp, box_b.timestamp = box_b.timestamp, box_a.timestamp
        self.notify_observers()
        return True

    def reset_boxes(self):
        """Remet toutes les boîtes non réservées à l'état EMPTY."""
        for box in self.boxes:
            if box.status != BoxStatus.RESERVED:
                box.set_status(BoxStatus.EMPTY)
        self.notify_observers()

    def _read_box_sizes(self, num_boxes: int) -> List[int]:
        base_dir = Path(__file__).resolve().parents[2]
        config_path = base_dir / "config" / "config.txt"
        sizes = [1] * num_boxes

        if not config_path.exists():
            return sizes

        with config_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip().lower()
                value = value.strip()
                if not key.startswith("box"):
                    continue
                index_str = key[3:]
                if not index_str.isdigit():
                    continue
                box_index = int(index_str) - 1
                if not (0 <= box_index < num_boxes):
                    continue
                try:
                    size = int(value)
                except ValueError:
                    continue
                if size not in (1, 2):
                    continue
                sizes[box_index] = size

        return sizes

    def load_pains(self):
        """Charge les pains depuis commandes.csv et remplit les boîtes."""
        base_dir = Path(__file__).resolve().parents[2]
        commandes_path = base_dir / "commandes" / "commandes.csv"
        if not commandes_path.exists():
            return
        if commandes_path.stat().st_size == 0:
            for box in self.boxes:
                if box.status != BoxStatus.RESERVED:
                    box.set_status(BoxStatus.EMPTY)
            self.notify_observers()
            return

        self.reset_boxes()
        
        def _parse_quantity(value: str) -> int:
            clean = value.strip().replace(",", ".")
            if not clean:
                return 0
            try:
                qty = int(float(clean))
            except ValueError:
                return 0
            return qty if qty >= 1 else 0

        def _strip_quotes(value: str) -> str:
            clean = value.strip()
            if len(clean) >= 2 and clean[0] == '"' and clean[-1] == '"':
                return clean[1:-1]
            return clean

        def _clean_bread_name(value: str) -> str:
            clean = value.replace("(p.)", "").strip()
            return clean

        def _read_invert_load() -> bool:
            config_path = base_dir / "config" / "config.txt"
            if not config_path.exists():
                return False
            with config_path.open("r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    if key.strip().lower() == "invertload":
                        return value.strip().lower() == "true"
            return False

        invert_load = _read_invert_load()
        box_order = list(reversed(self.boxes)) if invert_load else self.boxes

        def _find_empty_box(required_size: int) -> Optional[Box]:
            for box in box_order:
                if box.status == BoxStatus.EMPTY and box.size == required_size:
                    return box
            return None

        def _place_small_single(user_name: str, bread_name: str) -> bool:
            box = _find_empty_box(1)
            if box is None:
                box = _find_empty_box(2)
            if box is None:
                return False
            box.set_status(BoxStatus.OCCUPIED, user_name, bread_name)
            return True

        def _place_small_pair(user_name: str, bread_name: str) -> bool:
            box = _find_empty_box(2)
            if box is not None:
                combined = f"{bread_name}\n{bread_name}"
                box.set_status(BoxStatus.OCCUPIED, user_name, combined)
                return True
            if not _place_small_single(user_name, bread_name):
                return False
            if not _place_small_single(user_name, bread_name):
                return False
            return True

        in_section = False
        headers: list[str] | None = None
        filled_any = False

        with commandes_path.open("r", encoding="utf-8", newline="") as handle:
            for raw_line in handle:
                line = raw_line.strip("\n")
                if not line:
                    continue

                cells = [_strip_quotes(cell) for cell in line.split(";")]
                if headers is None:
                    headers = cells
                    continue
                if not in_section:
                    if any("Boîte à P1s" in cell for cell in cells):
                        in_section = True
                    continue

                if any(cell.startswith("Total") for cell in cells if cell):
                    break

                if len(cells) < 3:
                    continue

                user_name = cells[0]
                if not user_name:
                    continue

                for col_index in range(2, len(cells)):
                    bread_name = headers[col_index] if col_index < len(headers) else ""
                    bread_name = _clean_bread_name(bread_name)
                    qty = _parse_quantity(cells[col_index])
                    if qty < 1:
                        continue

                    is_large = "_L" in bread_name
                    if is_large:
                        for _ in range(qty):
                            box = _find_empty_box(2)
                            if box is None:
                                return
                            box.set_status(BoxStatus.OCCUPIED, user_name, bread_name)
                            filled_any = True
                        continue

                    pair_count = qty // 2
                    remainder = qty % 2
                    for _ in range(pair_count):
                        if not _place_small_pair(user_name, bread_name):
                            return
                        filled_any = True
                    for _ in range(remainder):
                        if not _place_small_single(user_name, bread_name):
                            return
                        filled_any = True

        if filled_any:
            self.notify_observers()

    def print_pain(self):
        """Affiche le contenu de chaque boîte."""
        for box in self.boxes:
            if box.status == BoxStatus.EMPTY:
                content = "EMPTY"
            else:
                user = box.user_id or ""
                bread = box.bread_name or ""
                content = f"{user} | {bread}"
            print(f"Box {box.id + 1}: {content}")
