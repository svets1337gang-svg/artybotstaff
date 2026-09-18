from flask import Flask
import os
import threading

app = Flask(__name__)

@app.route('/')
def health():
    return "OK", 200

@app.route('/ping')
def ping():
    return "pong", 200

def run_bot():
    """Запускает бота в отдельном процессе"""
    os.system("python bot.py")

if __name__ == "__main__":
    # Запускаем бота в фоне
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()

    # Запускаем веб-сервер
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
