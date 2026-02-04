import os
import telebot
import google.generativeai as genai
import threading
import gradio as gr

# Recupero delle chiavi dalle variabili d'ambiente
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

def avvia_bot():
    try:
        # Configurazione Google Gemini
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Configurazione Telegram
        bot = telebot.TeleBot(TELEGRAM_TOKEN)
        
        # Rimuove eventuali webhook precedenti per evitare errori 409
        bot.delete_webhook()
        
        @bot.message_handler(func=lambda m: True)
        def rispondi(m):
            try:
                # Generazione della risposta con Gemini
                response = model.generate_content(m.text)
                bot.reply_to(m, response.text)
            except Exception as e:
                bot.reply_to(m, "In questo momento non riesco a elaborare la richiesta. Riprova tra poco.")
                print(f"Errore Gemini: {e}")

        print("Bot in ascolto su Telegram...")
        bot.infinity_polling()
        
    except Exception as e:
        print(f"Errore critico all'avvio: {e}")

# Avvio del bot in un thread separato
threading.Thread(target=avvia_bot, daemon=True).start()

# Interfaccia Gradio per mantenere attivo il servizio su Render
def home(input_text):
    return "Il bot è attivo e in ascolto su Telegram."

app = gr.Interface(
    fn=home, 
    inputs="text", 
    outputs="text", 
    title="Moltbot Status Center",
    description="Se vedi questa pagina, il server è online."
)

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=10000)
