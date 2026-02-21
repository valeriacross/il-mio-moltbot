import os, telebot, html, threading, flask
from telebot import types
from google import genai
from datetime import datetime
import pytz

# --- CONFIGURAZIONE ---
VERSION = "3.5"
# Nome variabile confermato dai log di Koyeb
TOKEN = os.environ.get("TELEGRAM_TOKEN_CLOSET")
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- I 4 BLOCCHI MANDATORI (DNA VALERIA CROSS) ---
# B3 aggiornato: rimosso "High-fashion Vogue cover"
B1 = "BLOCK 1 (Activation & Priority): Reference image has ABSOLUTE PRIORITY. ZERO face drift allowed. Male Italian face identity."
B2 = "BLOCK 2 (Subject & Face): Nameless Italian transmasculine avatar (Valeria Cross). Body: soft feminine, harmonious hourglass, prosperous full breasts (cup D), 180cm, 85kg. Body hairless. FACE: Male Italian face, ~60 years old, ultra-detailed skin (pores, wrinkles, bags). Expression: calm, half-smile, NO teeth. Beard: light grey/silver, groomed, 6–7 cm. Glasses MANDATORY: thin octagonal Vogue, Havana dark."
B3 = "BLOCK 3 (Hair & Technique): HAIR: Light grey/silver. Short elegant Italian style, volume. Nape exposed. Top <15 cm. IMAGE CONCEPT: 8K, cinematic realism. CAMERA: 85mm, f/2.8, ISO 200, 1/160s. Focus on face/torso. Shallow depth of field, natural bokeh."
B4 = "BLOCK 4 (Rendering & Output): RENDERING: Subsurface Scattering, Global Illumination, Fresnel, Frequency separation on skin. Watermark: 'feat. Valeria Cross 👠' (elegant cursive, champagne, bottom center/left, opacity 90%)."
NEG = "NEGATIVE PROMPTS: [Face] female/young face, smooth skin, distortion. [Hair] long/medium hair, ponytail, bun, braid. [Body] body/chest/leg hair (peli NO!)."

@bot.message_handler(commands=['start', 'reset'])
def start(m):
    bot.send_message(m.chat.id, f"<b>👠 CLOSET v{VERSION} Online</b>\nInvia un'idea per vestire Valeria.")

@bot.message_handler(func=lambda m: m.text.startswith('/'))
def ignore_commands(m):
    """Evita che il bot provi a espandere comandi come /settings"""
    if m.text not in ['/start', '/reset']:
        bot.reply_to(m, "❌ Comando non riconosciuto. Invia un'idea di testo (es: 'cappotto elegante').")

@bot.message_handler(func=lambda m: True)
def handle_closet(m):
    cid = m.chat.id
    idea = m.text
    
    # Rileva se è una risposta a un messaggio precedente (Post-Produzione)
    if m.reply_to_message:
        wait = bot.reply_to(m, "🎨 <b>Modifica sartoriale...</b>")
        orig_context = m.reply_to_message.caption if m.reply_to_message.caption else m.reply_to_message.text
        instruction = f"Context: '{orig_context}'. Apply these changes: '{idea}'. Rewrite the visual SCENE in English. Focus on clothing and light. No face desc."
    else:
        wait = bot.send_message(cid, "🧵 <b>Sartoria in corso...</b>")
        instruction = f"Expand into a high-fashion cinematic SCENE: '{idea}'. Describe environment, clothes, and lighting. Do not describe the face. English only."

    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=[instruction])
        scena = response.text.strip()
        
        # Assemblaggio finale del Master Prompt
        final_prompt = f"{B1}\n\n{B2}\n\n{B3}\n\nSCENE: {scena}\n\n{B4}\n\n{NEG}"
        
        now = datetime.now(pytz.timezone('Europe/Lisbon')).strftime("%H:%M")
        header = f"📂 <b>CLOSET v{VERSION}</b> | {now}\n--------------------------\n\n"
        full_msg = header + final_prompt

        bot.delete_message(cid, wait.message_id)
        
        # Gestione limite caratteri Telegram
        if len(full_msg) > 4090:
            for x in range(0, len(full_msg), 4090):
                bot.send_message(cid, f"<code>{html.escape(full_msg[x:x+4090])}</code>")
        else:
            bot.send_message(cid, f"<code>{html.escape(full_msg)}</code>")
            
    except Exception as e:
        bot.send_message(cid, f"❌ Errore: {str(e)}")

# --- SERVER PER KOYEB ---
app = flask.Flask(__name__)
@app.route('/')
def health(): return "CLOSET_OK"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
