import os
import telebot
import google.generativeai as genai
import gradio as gr
import threading
import sys

# Forza la scrittura immediata dei log
def stampa(msg):
    print(msg, flush=True)

# 1. Recupero chiavi
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

def avvia_bot():
    stampa("--- ⚙️ TENTATIVO DI CONNESSIONE FINALE ---")
    try:
        # Configurazione Google
        genai.configure(api_key=G_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        bot = telebot.TeleBot(T_TOKEN)
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                stampa(f"--- 📩 Messaggio: {m.text} ---")
                res = model.generate_content(m.text)
                bot.reply_to(m, res.text)
                stampa("--- ✅ Risposta inviata! ---")
            except Exception as e_gemini:
                stampa(f"--- ❌ ERRORE GEMINI: {e_gemini} ---")
                bot.reply_to(m, f"Errore tecnico di Google: {e_gemini}")

        # Pulisce vecchie sessioni
        bot.delete_webhook()
        stampa("--- ✅ BOT PRONTO E IN ASCOLTO ---")
        
        # ABBIAMO TOLTO IL COMANDO CHE DAVA ERRORE QUI SOTTO:
        bot.infinity_polling()
        
    except Exception as e:
        stampa(f"--- ❌ ERRORE CRITICO: {e} ---")

# Lancio parallelo
threading.Thread(target=avvia_bot, daemon=True).start()

# Interfaccia di controllo
with gr.Blocks() as demo:
    gr.Markdown("# 🟢 Stato Bot Valeria")
    gr.Markdown("Server Render: ATTIVO")
demo.launch(server_name="0.0.0.0", server_port=10000)
