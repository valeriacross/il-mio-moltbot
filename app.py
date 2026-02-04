import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

def avvia_bot():
    print("--- ⚙️ DIAGNOSTICA MODELLI GOOGLE ---", flush=True)
    try:
        genai.configure(api_key=G_KEY)
        
        # Chiediamo a Google quali modelli puoi usare davvero
        modelli_disponibili = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        print(f"--- ✅ Modelli trovati: {modelli_disponibili} ---", flush=True)
        
        # Scegliamo il miglior modello disponibile nel tuo account
        if any("gemini-1.5-flash" in m for m in modelli_disponibili):
            nome_modello = "gemini-1.5-flash"
        elif any("gemini-pro" in m for m in modelli_disponibili):
            nome_modello = "gemini-pro"
        else:
            nome_modello = modelli_disponibili[0] if modelli_disponibili else None

        if not nome_modello:
            print("--- ❌ Nessun modello compatibile trovato! ---", flush=True)
            return

        print(f"--- 🚀 Uso il modello: {nome_modello} ---", flush=True)
        model = genai.GenerativeModel(nome_modello)
        bot = telebot.TeleBot(T_TOKEN)
        bot.delete_webhook()

        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                res = model.generate_content(m.text)
                bot.reply_to(m, res.text)
            except Exception as e:
                bot.reply_to(m, f"Errore: {e}")

        print("--- ✅ BOT IN ASCOLTO ---", flush=True)
        bot.infinity_polling()
    except Exception as e:
        print(f"--- ❌ ERRORE CRITICO: {e} ---", flush=True)

threading.Thread(target=avvia_bot, daemon=True).start()

with gr.Blocks() as demo:
    gr.Markdown(f"# Bot Valeria - Diagnostica Modelli")
demo.launch(server_name="0.0.0.0", server_port=10000)
                
