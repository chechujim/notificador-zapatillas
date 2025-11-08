import requests
from bs4 import BeautifulSoup
import time
import json
import os
from flask import Flask

# === CONFIGURACIÓN ===
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")  # Variable de entorno en Render
CHAT_ID = os.getenv("CHAT_ID")           # Variable de entorno en Render
CHECK_INTERVAL = 6 * 60 * 60             # Cada 6 horas (en segundos)
URL = "https://certcheck.worldathletics.org/FullList"
FILE_NAME = "zapatillas_previas.json"

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot activo y escuchando 🚀"

def get_zapatillas():
    """Descarga y analiza la lista de zapatillas desde World Athletics."""
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("table tbody tr")

    zapatillas = []
    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if cols:
            zapatillas.append(cols[0])  # Primer campo = nombre del modelo
    return zapatillas

def send_telegram_message(message):
    """Envía un mensaje a Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)

def main():
    """Compara la lista actual con la anterior y envía avisos si hay novedades."""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            previas = set(json.load(f))
    else:
        previas = set()

    actuales = set(get_zapatillas())
    nuevas = actuales - previas

    if nuevas:
        mensaje = "👟 Nuevas zapatillas registradas en World Athletics:\n" + "\n".join(nuevas)
        send_telegram_message(mensaje)
        print("Notificación enviada:", nuevas)

    with open(FILE_NAME, "w") as f:
        json.dump(list(actuales), f)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print("Error:", e)
        time.sleep(CHECK_INTERVAL)
