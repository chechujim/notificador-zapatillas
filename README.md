"""
notificador_zapatillas.py
Script definitivo para Render:
- Comprueba https://certcheck.worldathletics.org/FullList periódicamente
- Si detecta nuevas zapatillas, envía notificación a Telegram
- Expone mini web para que Render mantenga el servicio vivo
- Endpoints: / (status), /notify?msg=... (envío manual), /run_check (forzar chequeo)
"""

import os
import time
import json
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify

# ------------------- CONFIG -------------------
# Seguridad: preferible usar variables de entorno en Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")   # <- pon tu token en Render env var
CHAT_ID = os.getenv("CHAT_ID", "")                 # <- pon tu chat id en Render env var
# Intervalo por defecto: 6 horas (en segundos). Puedes sobreescribir con env var.
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", str(6 * 60 * 60)))
URL = "https://certcheck.worldathletics.org/FullList"
SEEN_FILE = "zapatillas_previas.json"
# -----------------------------------------------

app = Flask(__name__)

def log(*args):
    print("[notificador]", *args)

def enviar_telegram(texto):
    """Envía mensaje por Telegram; imprime error si falla."""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        log("WARN: TELEGRAM_TOKEN o CHAT_ID no configurados. No se enviará mensaje.")
        return False, "No token/chat"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": texto}
    try:
        r = requests.post(url, data=payload, timeout=15)
        if r.status_code == 200:
            log("Mensaje enviado a Telegram.")
            return True, r.text
        else:
            log("Error Telegram:", r.status_code, r.text)
            return False, r.text
    except Exception as e:
        log("Exception al enviar Telegram:", e)
        return False, str(e)

def fetch_shoes():
    """Descarga y parsea la lista de zapatillas.
       Devuelve lista de strings representando cada entrada."""
    try:
        r = requests.get(URL, timeout=20)
        r.raise_for_status()
    except Exception as e:
        log("Error descargando URL:", e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    # Intentamos parsear tabla estándar
    rows = soup.select("table tbody tr")
    zapatos = []
    if rows:
        for row in rows:
            cols = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            if cols:
                # Guardamos una representación sencilla: nombre + resto de campos si quieres
                zapatos.append(" | ".join(cols))
    else:
        # Fallback heurístico: buscar líneas con texto
        items = soup.find_all(["p", "li", "div"])
        for it in items:
            text = it.get_text(" ", strip=True)
            if text and len(text) > 30:  # heurística para evitar ruidos
                zapatos.append(text)

    # dedup manteniendo orden
    seen = set()
    clean = []
    for z in zapatos:
        if z not in seen:
            seen.add(z)
            clean.append(z)
    log(f"Parseadas {len(clean)} entradas.")
    return clean

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            log("No pude leer seen file:", e)
            return set()
    return set()

def save_seen(lst):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(lst), f, ensure_ascii=False, indent=2)
    except Exception as e:
        log("Error guardando seen file:", e)

def check_once():
    """Realiza una comprobación y notifica si hay novedades."""
    actuales = set(fetch_shoes())
    if not actuales:
        log("fetch_shoes devolvió vacío; se aborta check.")
        return {"status": "empty_fetch", "new": []}

    prev = load_seen()
    nuevas = sorted(list(actuales - prev))
    if nuevas:
        log(f"Detectadas {len(nuevas)} nuevas entradas.")
        mensaje = "👟 Nuevas zapatillas registradas en World Athletics:\n\n" + "\n\n".join(nuevas)
        success, resp = enviar_telegram(mensaje)
        if success:
            # actualizamos lista vista solo si envío ok
            save_seen(actuales)
            return {"status": "notified", "new": nuevas}
        else:
            log("No se pudo notificar; no actualizo seen file.")
            return {"status": "telegram_failed", "error": resp, "new": nuevas}
    else:
        log("Sin novedades.")
        # actualizar seen si no existía (primera ejecución)
        if not prev:
            save_seen(actuales)
        return {"status": "no_new", "new": []}

def background_loop():
    log(f"Bot arrancado — comprobando cada {CHECK_INTERVAL}s")
    # Primera comprobación al arrancar
    try:
        check_once()
    except Exception as e:
        log("Error en primera comprobación:", e)
    # Bucle principal
    while True:
        time.sleep(CHECK_INTERVAL)
        try:
            check_once()
        except Exception as e:
            log("Error en check:", e)

# ---- Flask endpoints ----
@app.route("/")
def index():
    return "✅ Notificador Zapatillas funcionando correctamente."

@app.route("/notify", methods=["GET"])
def notify():
    msg = request.args.get("msg", "👟 Notificación de prueba desde NotificadorZapatillas.")
    ok, resp = enviar_telegram(msg)
    return jsonify({"sent": ok, "response": resp})

@app.route("/run_check", methods=["GET"])
def run_check():
    result = check_once()
    return jsonify(result)

# Lanzamos el loop en hilo daemon antes de arrancar Flask
def start_background_thread():
    t = threading.Thread(target=background_loop, daemon=True)
    t.start()

# Entry point
if __name__ == "__main__":
    # Inicio en local: arrancar hilo y Flask
    start_background_thread()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
