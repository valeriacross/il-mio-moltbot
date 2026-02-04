import os
import telebot
import google.generativeai as genai
import gradio as gr
import threading

# 1. Recupero chiavi
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

def avvia_bot():
    print("--- ⚙️ TENTATIVO DI CONNESSIONE ---", flush=True)
    try:
        # Configurazione Google
        genai.configure(api_key=G_KEY)
        
        # ABBIAMO CAMBIATO IL NOME QUI SOTTO:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        bot = telebot.TeleBot(T_TOKEN)
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                print(f"--- 📩 Messaggio: {m.text} ---", flush=True)
                # Tentativo di generazione
                res = model.generate_content(m.text)
                bot.reply_to(m, res.text)
                print("--- ✅ Risposta inviata! ---", flush=True)
            except Exception as e_gemini:
                print(f"--- ❌ ERRORE GEMINI: {e_gemini} ---", flush=True)
                bot.reply_to(m, "Google ha avuto un singhiozzo, riprova tra un istante!")

        # Pulizia e avvio
        bot.delete_webhook()
        print("--- ✅ BOT PRONTO E IN ASCOLTO ---", flush=True)
        bot.infinity_polling()
        
    except Exception as e_critico:
        print(f"--- ❌ ERRORE CRITICO: {e_critico} ---", flush=True)

# Lancio pagina web e bot
threading.Thread(target=avvia_bot, daemon=True).start()

with gr.Blocks() as demo:
    gr.Markdown("# Diagnostica Bot Valeria")
demo.launch(server_name="0.0.0.0", server_port=10000)
        
