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
        # Usiamo il Pro che è più stabile per le API vecchie
        model = genai.GenerativeModel('gemini-pro')
        bot = telebot.TeleBot(T_TOKEN)
        
        # Forza la chiusura di ogni sessione precedente
        bot.delete_webhook()
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                res = model.generate_content(m.text)
                bot.reply_to(m, res.text)
            except Exception as e:
                bot.reply_to(m, f"Errore: {e}")
                
        print("--- ✅ BOT ONLINE CON NUOVO TOKEN ---", flush=True)
        bot.infinity_polling()
    except Exception as e:
        print(f"--- ❌ ERRORE: {e} ---", flush=True)

threading.Thread(target=avvia_bot, daemon=True).start()

def web():
    gr.Interface(fn=lambda x:x, inputs="text", outputs="text").launch(server_name="0.0.0.0", server_port=10000)

if __name__ == "__main__":
    web()
    
