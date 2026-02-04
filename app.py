import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

# Recupero chiavi
G_KEY = os.environ.get("GOOGLE_API_KEY")
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")

def avvia_bot():
    print("--- 🚀 FASE 1: Avvio setup ---")
    try:
        genai.configure(api_key=G_KEY)
        # Usiamo il nome corretto per la versione attuale
        model = genai.GenerativeModel('gemini-1.5-flash')
        bot = telebot.TeleBot(T_TOKEN)
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                print(f"--- 📩 Ricevuto messaggio: {m.text} ---")
                res = model.generate_content(m.text)
                bot.reply_to(m, res.text)
                print("--- ✅ Risposta inviata con successo! ---")
            except Exception as e_inner:
                print(f"--- ❌ Errore durante la risposta: {e_inner} ---")
                bot.reply_to(m, "Sto ricaricando i miei circuiti, riprova tra un istante!")
            
        print("--- ✅ FASE 3: Bot collegato a Telegram! ---")
        bot.infinity_polling()
    except Exception as e:
        print(f"--- ❌ ERRORE AVVIO: {e} ---")

# Avvio bot in background
threading.Thread(target=avvia_bot, daemon=True).start()

# Pagina web per Render
with gr.Blocks() as demo:
    gr.Markdown("# Bot Valeria Online 🟢")
demo.launch(server_name="0.0.0.0", server_port=10000)
