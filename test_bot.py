from telegram import Bot

# Sustituye por tu token y chat ID
TOKEN = "TU_TOKEN_DE_TELEGRAM"
CHAT_ID = 1779007230

bot = Bot(token=TOKEN)

# Mensaje de prueba
bot.send_message(chat_id=CHAT_ID, text="🚀 Test desde Render: el bot funciona correctamente")
