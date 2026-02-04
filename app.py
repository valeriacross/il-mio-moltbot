import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

def avvia_bot():
    print("--- 🚀 FASE 1: Avvio ---")
    # Questo ci dirà se la chiave è quella giusta senza mostrarla tutta
    if T_TOKEN:
        print(f"--- 🔑 Token rilevato! Inizia con: {T_TOKEN[:4]} ---")
    else:
        print("--- ❌ ERRORE: La variabile TELEGRAM_TOKEN è vuota! ---")
        
    try:
        genai.configure(api_key=G_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        bot = telebot.TeleBot(T_TOKEN)
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            res = model.generate_content(m.text)
            bot.reply_to(m, res.text)
            
        print("--- ✅ FASE 3: Bot pronto! ---")
        bot.infinity_polling()
    except Exception as e:
        print(f"--- ❌ ERRORE: {e} ---")

threading.Thread(target=avvia_bot, daemon=True).start()

with gr.Blocks() as demo:
    gr.Markdown("# Bot Online")
demo.launch(server_name="0.0.0.0", server_port=10000)
