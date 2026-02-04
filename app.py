import os
import telebot
import google.generativeai as genai
import gradio as gr
import threading
import sys

# Funzione per forzare la visibilità dei log su Render
def stampa(msg):
    print(msg, flush=True)

# 1. Recupero chiavi dai Settings di Render
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

def avvia_bot():
    stampa("--- ⚙️ TENTATIVO DI CONNESSIONE ---")
    try:
        # Configurazione Google Gemini
        genai.configure(api_key=G_KEY)
        
        # Usiamo il nome del modello standard
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Configurazione Telegram
        bot = telebot.TeleBot(T_TOKEN)
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                stampa(f"--- 📩 Messaggio: {m.text} ---")
                # Generazione risposta
                res = model.generate_content(m.text)
                bot.reply_to(m, res.text)
                stampa("--- ✅ Risposta inviata con successo! ---")
            except Exception as e_gemini:
                stampa(f"--- ❌ ERRORE GEMINI: {e_gemini} ---")
                # Il bot ti scriverà l'errore reale su Telegram
                bot.reply_to(m, f"Errore tecnico di Google: {e_gemini}")

        # Pulizia webhook per evitare l'errore 409 Conflict
        bot.delete_webhook()
        stampa("--- ✅ BOT PRONTO E IN ASCOLTO ---")
        bot.infinity_polling(skip_pending_updates=True)
        
    except Exception as e_critico:
        stampa(f"--- ❌ ERRORE CRITICO AVVIO: {e_critico} ---")

# Lancio del thread del bot (per farlo girare insieme alla pagina web)
threading.Thread(target=avvia_bot, daemon=True).start()

# Interfaccia Gradio (necessaria per mantenere il servizio "Live" su Render)
with gr.Blocks() as demo:
    gr.Markdown("# 🟢 Bot di Valeria Online")
    gr.Markdown("Se vedi questa pagina, il server su Render è attivo.")
    
demo.launch(server_name="0.0.0.0", server_port=10000)
