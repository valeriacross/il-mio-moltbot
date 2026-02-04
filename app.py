import os
import telebot
from google import genai
import threading
import gradio as gr

# Recupero chiavi
G_KEY = os.environ.get("GOOGLE_API_KEY")
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")

def avvia_bot():
    print("--- 🚀 FASE 1: Avvio con Nuovo SDK Google ---")
    try:
        # Nuovo sistema Google GenAI
        client = genai.Client(api_key=G_KEY)
        bot = telebot.TeleBot(T_TOKEN)
        
        # Pulizia per evitare l'errore 409 Conflict
        bot.remove_webhook(drop_pending_updates=True)
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                print(f"--- 📩 Messaggio: {m.text} ---")
                # Nuova sintassi per generare testo
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=m.text
                )
                bot.reply_to(m, response.text)
            except Exception as e_inner:
                print(f"--- ❌ Errore Gemini: {e_inner} ---")
                bot.reply_to(m, "Scusa, un piccolo intoppo tecnico. Riprova!")
            
        print("--- ✅ FASE 3: Bot Online e Aggiornato! ---")
        bot.infinity_polling(skip_pending_updates=True)
    except Exception as e:
        print(f"--- ❌ ERRORE AVVIO: {e} ---")

# Avvio in background
threading.Thread(target=avvia_bot, daemon=True).start()

# Interfaccia web
with gr.Blocks() as demo:
    gr.Markdown("# Bot Valeria Online 🟢 (Versione 2.0)")
demo.launch(server_name="0.0.0.0", server_port=10000)
