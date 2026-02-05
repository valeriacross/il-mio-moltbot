import os
import telebot
import google.generativeai as genai
import threading
import time
import gradio as gr

T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

def avvia_bot():
    try:
        # Configurazione con la nuova chiave
        genai.configure(api_key=G_KEY)
        
        # Proviamo il nome 'ufficiale' completo per evitare il 404
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        
        bot = telebot.TeleBot(T_TOKEN)
        
        # RESET AGGRESSIVO DEL WEBHOOK
        bot.remove_webhook()
        time.sleep(2) # Pausa per lasciare respirare Telegram
        
        @bot.message_handler(func=lambda m: True)
        def handle_message(m):
            try:
                # Test di risposta minimo
                response = model.generate_content(f"Rispondi in 5 parole: {m.text}")
                bot.reply_to(m, response.text)
            except Exception as e:
                bot.reply_to(m, f"❌ Errore Interno: {e}")

        print("--- ✅ MOLTBOT OPERATIVO ---", flush=True)
        # skip_pending pulisce i messaggi accumulati durante il crash
        bot.infinity_polling(skip_pending=True, timeout=60)
        
    except Exception as e:
        print(f"--- ❌ ERRORE AVVIO: {e} ---", flush=True)

# Gradio serve a tenere in vita il server su Render
def dummy_interface(input_text):
    return f"Bot Status: Online. Last input: {input_text}"

threading.Thread(target=avvia_bot, daemon=True).start()
gr.Interface(fn=dummy_interface, inputs="text", outputs="text").launch(server_name="0.0.0.0", server_port=10000)
