import os
import telebot
import google.generativeai as genai
import threading
import time
import gradio as gr

# Recupero credenziali
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

# --- MASTER PROMPT INTEGRALE ---
MASTER_PROMPT = """
Generate a high-resolution image using the uploaded image as a canvas and face reference, maintaining its original aspect ratio and exact proportions.

SUBJECT: Valeria Cross, transmaschile. Volto italiano 60 anni (capelli grigio platino ondulati, occhiali ottagonali Vogue Havana), corpo femminile morbido (180cm, 85kg, coppa D).

NEGATIVE PROMPT: No volto femminile, no lineamenti giovani, no pelle artificiale, no distorsioni. No capelli lunghi, no ponytail, no stili militari, no capelli neri o castani.

TECH SPECS: 85mm objective, f/2.8 aperture, ISO 200, shutter 1/160. Global Illumination, Ambient Occlusion, Subsurface Scattering on skin, Frequency Separation post-processing. 8K ultra-realistic resolution (4.2MP).

WATERMARK: MUST include refined signature "feat. Valeria Cross 👠" bottom left, cursive champagne script, 90% opacity.
"""

def avvia_bot():
    try:
        genai.configure(api_key=G_KEY)
        # Usiamo il Pro dell'account Wallycap
        model = genai.GenerativeModel(
            model_name='gemini-1.5-pro',
            system_instruction=MASTER_PROMPT
        )
        
        bot = telebot.TeleBot(T_TOKEN)
        bot.remove_webhook()
        time.sleep(1)
        
        @bot.message_handler(func=lambda m: True)
        def handle_message(m):
            try:
                # Generazione prompt/contenuto con Gemini Pro
                response = model.generate_content(m.text)
                bot.reply_to(m, response.text)
            except Exception as e:
                bot.reply_to(m, f"⚠️ Errore: {e}")

        print("--- ✅ MOLTBOT PRO VOGUE ONLINE ---", flush=True)
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"--- ❌ ERRORE CRITICO: {e} ---", flush=True)

threading.Thread(target=avvia_bot, daemon=True).start()
gr.Interface(fn=lambda x:x, inputs="text", outputs="text").launch(server_name="0.0.0.0", server_port=10000)
