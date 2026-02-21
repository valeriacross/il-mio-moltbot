import os, telebot, html, threading, flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types as genai_types
from io import BytesIO
from datetime import datetime
import pytz

# --- CONFIGURAZIONE ---
VERSION = "4.0"
TOKEN = os.environ.get("TELEGRAM_TOKEN_CLOSET")
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- BLOCCHI VALERIA CROSS ---
B1 = "BLOCK 1 (Activation & Priority): Reference image has ABSOLUTE PRIORITY. ZERO face drift allowed. Male Italian face identity."
B2 = "BLOCK 2 (Subject & Face): Nameless Italian transmasculine avatar (Valeria Cross). Body: soft feminine, harmonious hourglass, prosperous full breasts (cup D), 180cm, 85kg. Body hairless. FACE: Male Italian face, ~60 years old, ultra-detailed skin (pores, wrinkles, bags). Expression: calm, half-smile, NO teeth. Beard: light grey/silver, groomed, 6–7 cm. Glasses MANDATORY: thin octagonal Vogue, Havana dark."
B3 = "BLOCK 3 (Hair & Technique): HAIR: Light grey/silver. Short elegant Italian style, volume. Nape exposed. Top <15 cm. IMAGE CONCEPT: 8K, cinematic realism. CAMERA: 85mm, f/2.8, ISO 200, 1/160s. Focus on face/torso. Shallow depth of field, natural bokeh."
B4 = "BLOCK 4 (Rendering & Output): RENDERING: Subsurface Scattering, Global Illumination, Fresnel, Frequency separation on skin. Watermark: 'feat. Valeria Cross 👠' (elegant cursive, champagne, very small font size, bottom center/left, opacity 90%)."
NEG = "NEGATIVE PROMPTS: [Face] female/young face, smooth skin, distortion. [Hair] long/medium hair, ponytail, bun, braid. [Body] body/chest/leg hair (peli NO!)."

# --- STATO UTENTE ---
user_settings = {}

def get_settings(cid):
    if cid not in user_settings:
        user_settings[cid] = {'ratio': '3:4', 'count': 1}
    return user_settings[cid]

# --- MENU SETTINGS ---
@bot.message_handler(commands=['settings'])
def settings_menu(m):
    cid = m.chat.id
    current = get_settings(cid)
    markup = InlineKeyboardMarkup()
    
    # Formati (Senza 1:1)
    markup.row(
        InlineKeyboardButton(f"ASPECT: {current['ratio']}", callback_data="ignore"),
        InlineKeyboardButton("3:4", callback_data="ar_3:4"),
        InlineKeyboardButton("9:16", callback_data="ar_9:16"),
        InlineKeyboardButton("16:9", callback_data="ar_16:9")
    )
    # Numero Immagini
    markup.row(
        InlineKeyboardButton(f"IMMAGINI: {current['count']}", callback_data="ignore"),
        InlineKeyboardButton("1", callback_data="n_1"),
        InlineKeyboardButton("2", callback_data="n_2"),
        InlineKeyboardButton("3", callback_data="n_3"),
        InlineKeyboardButton("4", callback_data="n_4")
    )
    bot.send_message(cid, "⚙️ <b>Impostazioni CLOSET</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    data = call.data
    if data == "ignore": return
    
    current = get_settings(cid)
    if data.startswith("ar_"):
        current['ratio'] = data.split("_")[1]
    elif data.startswith("n_"):
        current['count'] = int(data.split("_")[1])
        
    bot.answer_callback_query(call.id, "Impostazioni aggiornate!")
    bot.delete_message(cid, call.message.message_id)
    settings_menu(call.message)

@bot.message_handler(commands=['start', 'reset'])
def start(m):
    bot.send_message(m.chat.id, f"<b>👠 CLOSET v{VERSION} Online</b>\nInvia un'idea o usa /settings.")

# --- GENERAZIONE ---
@bot.message_handler(func=lambda m: not m.text.startswith('/'))
def generate_closet(m):
    cid = m.chat.id
    idea = m.text
    settings = get_settings(cid)
    
    wait = bot.send_message(cid, "🧠 <b>Sintesi prompt in corso...</b>")
    
    # 1. Ferma i romanzi: Istruzione tassativa per avere solo keyword
    instruction = (
        f"Convert this idea into a concise list of visual keywords for an image generator: '{idea}'. "
        f"Focus ONLY on clothes, lighting, and environment. NO narrative, NO verbs, NO full sentences. "
        f"Just comma-separated tags. Max 30 words. English only."
    )

    try:
        # Generazione Prompt corto
        response = client.models.generate_content(model="gemini-2.0-flash", contents=[instruction])
        scena_keywords = response.text.strip()
        
        final_prompt = f"{B1}\n\n{B2}\n\n{B3}\n\nSCENE: {scena_keywords}\n\n{B4}\n\n{NEG}"
        
        bot.edit_message_text("🎨 <b>Generazione immagine in corso...</b>", cid, wait.message_id)
        
        # 2. Generazione Immagine con Imagen 3
        result = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=final_prompt,
            config=genai_types.GenerateImagesConfig(
                number_of_images=settings['count'],
                aspect_ratio=settings['ratio'],
                output_mime_type="image/jpeg",
                person_generation="ALLOW_ADULT"
            )
        )
        
        # Invio Foto
        for generated_image in result.generated_images:
            image_stream = BytesIO(generated_image.image.image_bytes)
            bot.send_photo(cid, image_stream, caption=f"<code>{html.escape(scena_keywords)}</code>")
            
        bot.delete_message(cid, wait.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Errore: {str(e)}", cid, wait.message_id)

# --- SERVER KOYEB ---
app = flask.Flask(__name__)
@app.route('/')
def health(): return "CLOSET_OK"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
