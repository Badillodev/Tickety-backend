import json
import os
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent
CONFIG_FILE = CONFIG_DIR / "config.local.json"

def load_config():
    """Carga la configuración desde el archivo local JSON"""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Archivo de configuración no encontrado: {CONFIG_FILE}\n"
            f"Copia config.example.json a config.local.json y rellena los valores"
        )
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

config = load_config()

# Credenciales de base de datos
DATABASE_URL = config.get('DATABASE_URL', 'sqlite:///./tickety.db')

# Otras configuraciones
DEBUG = config.get('debug', False)
ENVIRONMENT = config.get('environment', 'development')

GOOGLE_CLIENT_ID = config.get('GOOGLE_CLIENT_ID', '')
JWT_SECRET = config.get('JWT_SECRET', '')
FRONTEND_URL = config.get('FRONTEND_URL', '')
STRIPE_SECRET_KEY = config.get('STRIPE_SECRET_KEY', '')
JWT_ALGORITHM = config.get('JWT_ALGORITHM', '')

print(f"[CONFIG] Entorno: {ENVIRONMENT}")
print(f"[CONFIG] Debug: {DEBUG}")
print(f"[CONFIG] DATABASE_URL: {DATABASE_URL}")
print(f"[CONFIG] GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")
print(f"[CONFIG] JWT_SECRET: {'*' * len(JWT_SECRET)}")
print(f"[CONFIG] FRONTEND_URL: {FRONTEND_URL}")
print(f"[CONFIG] STRIPE_SECRET_KEY: {'*' * len(STRIPE_SECRET_KEY)}")
print(f"[CONFIG] JWT_ALGORITHM: {JWT_ALGORITHM}")