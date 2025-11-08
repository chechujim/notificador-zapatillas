import os
import time
import requests
from bs4 import BeautifulSoup
import telegram
from threading import Thread
from flask import Flask

# ========================
# Configuración del Bot
# ========================
TOKEN = os.getenv("BOT_TOKEN")   # Poner tu token de Telegram en Render
CHAT_ID = os.getenv("CHAT_ID")   # Poner tu chat_id en Render
bot = telegram.Bot(token=TOKEN)

# ========================
# Función de Scraping
# ========================
def revisar_zapatillas():
    while True:
        try:
            url = "https://www.tusitio.com/zapatillas"  # Cambia a la URL real
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            # Ejemplo: buscar disponibilidad
            disponible = soup.find("span", class_="disponible")
            if disponible and "agotado" not in disponible.text.lower():
                bot.send_message(chat_id=CHAT_ID, text="¡Zapatilla disponible! " + url)
            else:
                print("Nada nuevo, seguimos esperando.")

        except Exception as e:
            print("Error revisando zapatillas:", e)
        time.sleep(60*5)  # Revisar cada 5 minutos

# ========================
# Iniciar Bot en Hilo
# ========================
Thread(target=revisar_zapatillas).start()

# ========================
# Servidor Flask mínimo
# ========================
app = Flask("notificador")

@app.route("/")
def home():
    return "Bot corriendo!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
