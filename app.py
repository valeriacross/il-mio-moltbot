import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

# Recupero chiavi
G_KEY = os.environ.get("GOOGLE_API_KEY")
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")

def avvia_bot():
    try:
        genai.configure(api_key=G_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        bot = telebot.TeleBot(T_TOKEN)
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            res = model.generate_content(m.text)
            bot.reply_to(m, res.text)
            
        bot.infinity_polling()
    except Exception as e:
        print(f"Errore: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()

with gr.Blocks() as demo:
    gr.Markdown("# Bot Online su Render 🟢")
demo.launch(server_name="0.0.0.0", server_port=10000)
