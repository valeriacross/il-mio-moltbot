import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

# MASTER PROMPT INTEGRALE CON TUTTE LE TUE DIRETTIVE
SYSTEM_INSTRUCTIONS = """
Generate a high-resolution image using the uploaded image as a canvas and face reference, maintaining its original aspect ratio and exact proportions. If no reference image is provided, generate the scene from scratch.

SOGGETTO: Valeria Cross, transmaschile. Volto italiano 60 anni, sguardo saggio, rughe naturali. Capelli grigio platino ondulati (15cm sopra, corti ai lati). Occhiali da vista ottagonali Vogue Havana dark. Corpo femminile morbido (180cm, 85kg, coppa D), pelle depilata.

PARAMETRI FOTOGRAFICI OBBLIGATORI: Apertura f/2.8, ISO 200, shutter 1/160, obiettivo 85mm. Messa a fuoco su torso e volto, bokeh naturale, luce calda e soffusa. Finish glossy 8K.

RENDERING: Global Illumination, Ambient Occlusion, Fresnel Effect, subsurface scattering sulla pelle, frequency separation controllata.

WATERMARK: In basso a sinistra, firma 'feat. Valeria Cross 👠' in corsivo champagne elegante, opacità 90%.

NEGATIVE PROMPT: No occhiali da sole, no volto femminile/giovane, no pelle artificiale, no capelli lunghi/neri/castani, no 1:1 format.
"""

def avvia_bot():
    try:
        genai.configure(api_key=G_KEY)
        # Usiamo il modello Pro come richiesto
        model = genai.GenerativeModel(
            model_name='gemini-1.5-pro',
            system_instruction=SYSTEM_INSTRUCTIONS
        )
        
        bot = telebot.TeleBot(T_TOKEN)
        bot.delete_webhook()
        
        @bot.message_handler(func=lambda m: True)
        def handle_message(m):
            try:
                # Risposta diretta usando il modello Pro
                response = model.generate_content(m.text)
                bot.reply_to(m, response.text)
            except Exception as e:
                # Se superi la quota (Errore 429), il bot te lo dirà gentilmente
                if "429" in str(e):
                    bot.reply_to(m, "Valeria, Google ci sta chiedendo di rallentare un istante. Riprova tra 30 secondi.")
                else:
                    bot.reply_to(m, f"⚠️ Errore Google: {e}")

        print("--- ✅ MOLTBOT PRO IN ASCOLTO ---", flush=True)
        bot.infinity_polling()
    except Exception as e:
        print(f"--- ❌ CRASH ALL'AVVIO: {e} ---", flush=True)

threading.Thread(target=avvia_bot, daemon=True).start()
gr.Interface(fn=lambda x:x, inputs="text", outputs="text", title="Moltbot Center").launch(server_name="0.0.0.0", server_port=10000)
