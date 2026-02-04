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
        
        # --- SCOPERTA AUTOMATICA DEL MODELLO ---
        # Chiediamo a Google la lista dei modelli che puoi usare davvero
        modelli_disponibili = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if not modelli_disponibili:
            # Se la lista è vuota, il problema è la chiave o la regione
            nome_modello = None
        else:
            # Prendiamo il primo modello della lista (di solito il più compatibile)
            nome_modello = modelli_disponibili[0]
            print(f"--- 🚀 Modello selezionato automaticamente: {nome_modello} ---", flush=True)

        bot = telebot.TeleBot(T_TOKEN)
        bot.delete_webhook()
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            if not nome_modello:
                bot.reply_to(m, "⚠️ Errore critico: Google non mi mostra nessun modello disponibile per la tua chiave.")
                return
            try:
                model = genai.GenerativeModel(nome_modello)
                response = model.generate_content(m.text)
                bot.reply_to(m, response.text)
            except Exception as e:
                bot.reply_to(m, f"⚠️ ERRORE GOOGLE: {e}")

        print("--- ✅ BOT ATTIVO ---", flush=True)
        bot.infinity_polling()
        
    except Exception as e:
        print(f"--- ❌ ERRORE AVVIO: {e} ---", flush=True)

threading.Thread(target=avvia_bot, daemon=True).start()
gr.Interface(fn=lambda x: x, inputs="text", outputs="text", title="Moltbot Diagnostic").launch(server_name="0.0.0.0", server_port=10000)
