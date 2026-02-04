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
        # Usiamo il modello più stabile
        model = genai.GenerativeModel('gemini-1.5-flash')
        bot = telebot.TeleBot(T_TOKEN)
        bot.remove_webhook(drop_pending_updates=True)
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                # Chiediamo a Gemini di rispondere
                res = model.generate_content(m.text)
                bot.reply_to(m, res.text)
            except Exception as e_gemini:
                # Se Gemini fallisce, ci dice perché direttamente su Telegram!
                bot.reply_to(m, f"Errore del cervello: {e_gemini}")
            
        bot.infinity_polling(skip_pending_updates=True)
    except Exception as e:
        print(f"Errore avvio: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()

with gr.Blocks() as demo:
    gr.Markdown("# Bot di Valeria Online")
demo.launch(server_name="0.0.0.0", server_port=10000)
# Avvio
threading.Thread(target=avvia_bot, daemon=True).start()

# Interfaccia Gradio
with gr.Blocks() as demo:
    gr.Markdown("# Bot Valeria: Stato Online 🟢")
demo.launch(server_name="0.0.0.0", server_port=10000)
