import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

# Recupero chiavi
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

def avvia_bot():
    try:
        # Configurazione con la NUOVA chiave
        genai.configure(api_key=G_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        bot = telebot.TeleBot(T_TOKEN)
        bot.delete_webhook() # Pulisce eventuali conflitti 409

        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                # Se la chiave è nuova, questo DEVE funzionare
                res = model.generate_content(m.text)
                bot.reply_to(m, res.text)
            except Exception as e:
                bot.reply_to(m, f"Errore Google: {e}")

        print("--- ✅ BOT ONLINE CON NUOVA CHIAVE ---")
        bot.infinity_polling()
    except Exception as e:
        print(f"--- ❌ ERRORE AVVIO: {e} ---")

# Lancio thread e interfaccia
threading.Thread(target=avvia_bot, daemon=True).start()
gr.Interface(fn=lambda x:x, inputs="text", outputs="text").launch(server_name="0.0.0.0", server_port=10000)
