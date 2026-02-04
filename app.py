import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

def avvia_bot():
    try:
        genai.configure(api_key=G_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        bot = telebot.TeleBot(T_TOKEN)
        
        # --- AGGIUNGI QUESTA RIGA PER RISOLVERE IL CONFLITTO ---
        bot.remove_webhook(drop_pending_updates=True)
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            res = model.generate_content(m.text)
            bot.reply_to(m, res.text)
            
        print("--- ✅ Bot in ascolto! ---")
        # --- AGGIUNGI skip_pending_updates=True QUI SOTTO ---
        bot.infinity_polling(skip_pending_updates=True)
    except Exception as e:
        print(f"--- ❌ ERRORE: {e} ---")

threading.Thread(target=avvia_bot, daemon=True).start()

with gr.Blocks() as demo:
    gr.Markdown("# Bot Online")
demo.launch(server_name="0.0.0.0", server_port=10000)
