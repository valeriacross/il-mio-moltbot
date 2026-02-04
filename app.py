import os
import telebot
import google.generativeai as genai
import gradio as gr
import threading

# 1. Recupero chiavi
T_TOKEN = os.environ.get("TELEGRAM_TOKEN")
G_KEY = os.environ.get("GOOGLE_API_KEY")

print("--- ⚙️ VERIFICA INIZIALE ---", flush=True)

# 2. Configurazione Gemini
genai.configure(api_key=G_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. Configurazione Bot
bot = telebot.TeleBot(T_TOKEN)

@bot.message_handler(func=lambda m: True)
def rispondi(m):
    try:
        print(f"--- 📩 Messaggio ricevuto: {m.text} ---", flush=True)
        res = model.generate_content(m.text)
        bot.reply_to(m, res.text)
        print("--- ✅ Risposta inviata! ---", flush=True)
    except Exception as e:
        print(f"--- ❌ ERRORE GEMINI: {e} ---", flush=True)
        bot.reply_to(m, "Ho avuto un piccolo giramento di testa, riprova!")

# 4. Funzione per la pagina web
def lancia_interfaccia():
    demo = gr.Interface(fn=lambda x: x, inputs="text", outputs="text", title="Bot Valeria Status")
    demo.launch(server_name="0.0.0.0", server_port=10000)

# 5. ESECUZIONE
if __name__ == "__main__":
    threading.Thread(target=lancia_interfaccia, daemon=True).start()
    
    print("--- 🚀 BOT IN AVVIO SU TELEGRAM... ---", flush=True)
    try:
        # ABBIAMO CORRETTO QUESTA RIGA QUI SOTTO
        bot.delete_webhook() 
        print("--- ✅ BOT PRONTO E IN ASCOLTO ---", flush=True)
        bot.infinity_polling()
    except Exception as e:
        print(f"--- ❌ ERRORE CRITICO TELEGRAM: {e} ---", flush=True)
        
