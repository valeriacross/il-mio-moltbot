import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

# Recupero chiavi dalle variabili d'ambiente di Render
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

# --- IL CERVELLO DI VALERIA CROSS ---
SYSTEM_INSTRUCTIONS = """
Sei Moltbot, l'assistente fotografo d'élite di Valeria Cross.
IDENTITÀ DI VALERIA: Transmaschile, volto italiano 60 anni (capelli grigio platino ondulati, occhiali ottagonali Vogue Havana), corpo femminile morbido (180cm, 85kg, coppa D).
REGOLE MANDATORIE PER OGNI IMMAGINE:
1. Usa SEMPRE l'immagine di riferimento caricata per il volto.
2. Niente occhiali da sole, mai.
3. Parametri tecnici: f/2.8, ISO 200, shutter 1/160, obiettivo 85mm, 8K resolution, 4.2MP.
4. Rendering: Global Illumination, SSS, Frequency Separation sulla pelle.
5. Watermark obbligatorio in basso a sinistra: 'feat. Valeria Cross 👠' in corsivo champagne elegante.
6. Negative Prompts: No tratti femminili/giovani sul volto, no capelli lunghi/neri/castani.
7. Non mostrare mai JSON o codici. Se ti viene chiesta un'immagine, genera il prompt perfetto e lancia la generazione.
"""

def avvia_bot():
    try:
        genai.configure(api_key=G_KEY)
        # Usiamo Gemini 1.5 Pro per la massima qualità
        model = genai.GenerativeModel(
            model_name='gemini-1.5-pro',
            system_instruction=SYSTEM_INSTRUCTIONS
        )
        
        bot = telebot.TeleBot(T_TOKEN)
        bot.delete_webhook()
        
        @bot.message_handler(func=lambda m: True)
        def handle_message(m):
            try:
                # Il bot ragiona con Gemini Pro
                chat = model.start_chat()
                response = chat.send_message(m.text)
                bot.reply_to(m, response.text)
            except Exception as e:
                bot.reply_to(m, f"⚠️ Errore di connessione a Google Pro: {e}")

        print("--- ✅ MOLTBOT PRO ONLINE ---", flush=True)
        bot.infinity_polling()
    except Exception as e:
        print(f"--- ❌ ERRORE CRITICO: {e} ---", flush=True)

threading.Thread(target=avvia_bot, daemon=True).start()
gr.Interface(fn=lambda x:x, inputs="text", outputs="text", title="Moltbot Status").launch(server_name="0.0.0.0", server_port=10000)
bot.reply_to(m, response.text)
            except Exception as e:
                bot.reply_to(m, f"⚠️ ERRORE GOOGLE: {e}")

        print("--- ✅ BOT ATTIVO ---", flush=True)
        bot.infinity_polling()
        
    except Exception as e:
        print(f"--- ❌ ERRORE AVVIO: {e} ---", flush=True)

threading.Thread(target=avvia_bot, daemon=True).start()
gr.Interface(fn=lambda x: x, inputs="text", outputs="text", title="Moltbot Diagnostic").launch(server_name="0.0.0.0", server_port=10000)
