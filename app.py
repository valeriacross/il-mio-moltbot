import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

# Recupero chiavi
G_KEY = os.environ.get("GOOGLE_API_KEY")
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")

def avvia_bot():
    print("--- 🚀 AVVIO VERSIONE STABILE ---")
    try:
        genai.configure(api_key=G_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        bot = telebot.TeleBot(T_TOKEN)
        
        # Questa riga è magica: uccide ogni connessione vecchia/conflitto
        bot.remove_webhook(drop_pending_updates=True)
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                print(f"--- 📩 Ricevuto: {m.text} ---")
                res = model.generate_content(m.text)
                bot.reply_to(m, res.text)
            except Exception as e_inner:
                print(f"--- ❌ Errore: {e_inner} ---")
                bot.reply_to(m, "Sto riordinando le idee, riprova tra un attimo!")
            
        print("--- ✅ BOT PRONTO E IN ASCOLTO ---")
        # skip_pending_updates evita che il bot risponda a vecchi messaggi tutti insieme
        bot.infinity_polling(skip_pending_updates=True)
    except Exception as e:
        print(f"--- ❌ ERRORE CRITICO: {e} ---")

# Avvio
threading.Thread(target=avvia_bot, daemon=True).start()

# Interfaccia Gradio
with gr.Blocks() as demo:
    gr.Markdown("# Bot Valeria: Stato Online 🟢")
demo.launch(server_name="0.0.0.0", server_port=10000)
