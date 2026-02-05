import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

# Setup chiavi
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

# Istruzioni di Sistema (Il tuo Master Prompt)
SYSTEM_INSTRUCTIONS = """
Generate a high-resolution image using the uploaded image as a canvas and face reference, maintaining its original aspect ratio and exact proportions. 

SOGGETTO: Valeria Cross, transmaschile. Volto italiano 60 anni, capelli grigio platino ondulati, occhiali da vista ottagonali Vogue Havana. Corpo femminile morbido (180cm, 85kg, coppa D).

REGOLE: Niente occhiali da sole. Parametri: f/2.8, 85mm, Global Illumination, SSS, Frequency Separation. 
WATERMARK: 'feat. Valeria Cross 👠' in basso a sinistra.
"""

def avvia_bot():
    try:
        genai.configure(api_key=G_KEY)
        # Usiamo il modello che Google ha mostrato di riconoscere nel tuo ultimo log
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash', 
            system_instruction=SYSTEM_INSTRUCTIONS
        )
        
        bot = telebot.TeleBot(T_TOKEN)
        bot.remove_webhook() # Pulisce eventuali connessioni vecchie
        
        @bot.message_handler(func=lambda m: True)
        def handle_message(m):
            try:
                response = model.generate_content(m.text)
                bot.reply_to(m, response.text)
            except Exception as e:
                bot.reply_to(m, f"⚠️ Nota: {e}")

        # skip_pending=True evita che il bot risponda a vecchi messaggi tutti insieme al riavvio
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Errore: {e}")

threading.Thread(target=avvia_bot, daemon=True).start()
gr.Interface(fn=lambda x:x, inputs="text", outputs="text").launch(server_name="0.0.0.0", server_port=10000)
