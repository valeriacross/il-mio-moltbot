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
        # Il modello più 'malleabile' per il piano free
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        bot = telebot.TeleBot(T_TOKEN)
        bot.remove_webhook()
        
        @bot.message_handler(func=lambda m: True)
        def handle_message(m):
            try:
                # Prompt ultra-semplice per non intasare i token
                response = model.generate_content(f"Rispondi brevemente: {m.text}")
                bot.reply_to(m, response.text)
            except Exception as e:
                bot.reply_to(m, f"❌ Errore API: {e}")

        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Crash: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()
gr.Interface(fn=lambda x:x, inputs="text", outputs="text").launch(server_name="0.0.0.0", server_port=10000)
