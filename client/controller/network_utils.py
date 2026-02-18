"""
Utilitaires reseau.
"""

from __future__ import annotations
from pathlib import Path
import re
import requests
import socket


def _read_config(config_path: Path) -> tuple[str, str]:
	email = ""
	password = ""
	with config_path.open("r", encoding="utf-8") as handle:
		for raw_line in handle:
			line = raw_line.strip()
			if not line or line.startswith("#"):
				continue
			if "=" not in line:
				continue
			key, value = line.split("=", 1)
			key = key.strip().lower()
			value = value.strip()
			if key == "email":
				email = value
			elif key == "password":
				password = value

	if not email or not password:
		raise ValueError("config.txt doit contenir email=... et password=...")

	return email, password


def _extract_csrf(html: str) -> tuple[str, str] | None:
	match = re.search(
		r"<input[^>]*type=[\"']hidden[\"'][^>]*>",
		html,
		flags=re.IGNORECASE,
	)
	if not match:
		return None

	input_tag = match.group(0)
	name_match = re.search(r"name=[\"']([^\"']+)[\"']", input_tag, re.IGNORECASE)
	value_match = re.search(r"value=[\"']([^\"']*)[\"']", input_tag, re.IGNORECASE)
	if not name_match or not value_match:
		return None

	name = name_match.group(1)
	value = value_match.group(1)
	if "csrf" not in name.lower():
		return None

	return name, value

def get_commandes(date: str) -> Path:
	"""
	Telecharge les commandes pour une date (YYYY-MM-DD) et ecrit le CSV.
	"""
	base_dir = Path(__file__).resolve().parents[2]
	config_path = base_dir / "config" / "config.txt"
	output_path = base_dir / "commandes" / "commandes.csv"

	email, password = _read_config(config_path)

	login_url = "https://admin.souke.fr/site/login"
	export_url = "https://admin.souke.fr/distribution/export"

	payload = {
		"LoginForm[email]": email,
		"LoginForm[password]": password,
	}

	output_path.parent.mkdir(parents=True, exist_ok=True)

	with requests.Session() as session:
		response = session.get(login_url, timeout=30)
		response.raise_for_status()
		csrf = _extract_csrf(response.text)
		if csrf:
			payload[csrf[0]] = csrf[1]

		response = session.post(login_url, data=payload, timeout=30)
		response.raise_for_status()

		response = session.get(
			export_url,
			params={"name": "orders1_csv", "date": date},
			timeout=30,
		)
		response.raise_for_status()

		output_path.write_text(response.text, encoding="utf-8")

	return output_path


def check_arduino_connection(ip: str, port: int, timeout: float = 2.0) -> bool:
	"""
	Vérifie si l'Arduino est accessible via TCP.
	
	Args:
		ip: Adresse IP de l'Arduino
		port: Port de connexion
		timeout: Délai d'attente en secondes (défaut: 2.0)
	
	Returns:
		True si la connexion est établie, False sinon
	"""
	try:
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
			sock.settimeout(timeout)
			sock.connect((ip, port))
			return True
	except (socket.timeout, socket.error, OSError):
		return False


def send_arduino_command(ip: str, port: int, message: str, timeout: float = 5.0, buffer_size: int = 256) -> tuple[bool, str]:
	"""
	Envoie une commande à l'Arduino via TCP et lit la réponse.
	
	Args:
		ip: Adresse IP de l'Arduino
		port: Port de connexion
		message: Message à envoyer (un point sera ajouté automatiquement)
		timeout: Délai d'attente en secondes (défaut: 5.0)
		buffer_size: Taille du buffer de réception en octets (défaut: 256)
	
	Returns:
		Tuple (success, response) où success indique si l'envoi a réussi
		et response contient la réponse de l'Arduino ou un message d'erreur
	"""
	try:
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
			sock.settimeout(timeout)
			sock.connect((ip, port))
			
			# Ajouter un point à la fin du message et encoder en ASCII
			full_message = message + "."
			data = full_message.encode('ascii')
			
			# Envoyer les données
			sock.sendall(data)
			
			# Lire la réponse du serveur
			response_data = sock.recv(buffer_size)
			response = response_data.decode('ascii', errors='ignore')
			
			return (True, response)
			
	except socket.timeout:
		return (False, "Timeout: pas de réponse de l'Arduino")
	except socket.error as e:
		return (False, f"Erreur de socket: {e}")
	except OSError as e:
		return (False, f"Erreur: {e}")
	except Exception as e:
		return (False, f"Erreur inattendue: {e}")
