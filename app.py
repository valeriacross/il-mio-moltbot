import os
import telebot
import google.generativeai as genai
import threading
import time
import gradio as gr

# Chiavi configurate su Render
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

# MASTER PROMPT: La tua identità fotografica
SYSTEM_INSTRUCTION = """
Sei Moltbot, assistente di Valeria Cross. 
REGOLE FISSE:
- Volto: Usa sempre l'immagine di riferimento (italiano, 60 anni, occhiali Vogue Havana, capelli grigio platino).
- Fisico: 180cm, 85kg, coppa D, transmaschile.
- Foto: 85mm, f/2.8, 8K, Global Illumination, Frequency Separation.
- Watermark: 'feat. Valeria Cross 👠' in basso a sinistra, corsivo champagne, opacità 90%.
"""

def avvia_bot():
    try:
        genai.configure(api_key=G_KEY)
        # Il modello più stabile per evitare il 404
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash-latest',
            system_instruction=SYSTEM_INSTRUCTION
        )
        
        bot = telebot.TeleBot(T_TOKEN)
        bot.remove_webhook()
        time.sleep(1)
        
        @bot.message_handler(func=lambda m: True)
        def handle_message(m):
            try:
                response = model.generate_content(m.text)
                bot.reply_to(m, response.text)
            except Exception as e:
                bot.reply_to(m, f"⚠️ Nota: {e}")

        print("--- ✅ MOLTBOT OPERATIVO ---", flush=True)
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Errore Avvio: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()
gr.Interface(fn=lambda x:x, inputs="text", outputs="text").launch(server_name="0.0.0.0", server_port=10000)
