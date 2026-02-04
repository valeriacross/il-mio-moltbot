import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

# Recupero delle chiavi
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

def avvia_bot():
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # CAMBIATO: Usiamo il nome più compatibile in assoluto
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        bot = telebot.TeleBot(TELEGRAM_TOKEN)
        bot.delete_webhook()
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                response = model.generate_content(m.text)
                bot.reply_to(m, response.text)
            except Exception as e:
                # Ci scriverà l'errore se il modello ha ancora problemi
                bot.reply_to(m, f"⚠️ DEBUG ERRORE: {e}")

        print("--- ✅ BOT IN ASCOLTO ---", flush=True)
        bot.infinity_polling()
        
    except Exception as e:
        print(f"--- ❌ ERRORE CRITICO: {e} ---", flush=True)

threading.Thread(target=avvia_bot, daemon=True).start()

app = gr.Interface(fn=lambda x: x, inputs="text", outputs="text", title="Moltbot Status Center")
if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=10000)
    
