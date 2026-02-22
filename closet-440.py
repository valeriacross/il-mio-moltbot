import os, telebot, html, threading, flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types as genai_types
from io import BytesIO
from datetime import datetime
import pytz

# --- CONFIGURAZIONE ---
VERSION = "4.4"
TOKEN = os.environ.get("TELEGRAM_TOKEN_CLOSET")
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- CARICAMENTO MASTER FACE ---
def get_face_part():
    try:
        if os.path.exists("master_face.png"):
            with open("master_face.png", "rb") as f:
                return genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
        return None
    except Exception as e:
        print(f"❌ Errore caricamento master_face: {e}")
        return None

MASTER_PART = get_face_part()

# --- BLOCCHI VALERIA CROSS ---
B1 = "BLOCK 1 (Activation & Priority): Reference image has ABSOLUTE PRIORITY. ZERO face drift allowed. Male Italian face identity."
B2 = "BLOCK 2 (Subject & Face): Nameless Italian transmasculine avatar (Valeria Cross). Body: soft feminine, harmonious hourglass, prosperous full breasts (cup D), 180cm, 85kg. Body hairless. FACE: Male Italian face, ~60 years old, ultra-detailed skin (pores, wrinkles, bags). Expression: calm, half-smile, NO teeth. Beard: light grey/silver, groomed, 6–7 cm. Glasses MANDATORY: thin octagonal Vogue, Havana dark."
B3 = "BLOCK 3 (Hair & Technique): HAIR: Light grey/silver. Short elegant Italian style, volume. Nape exposed. Top <15 cm. IMAGE CONCEPT: 8K, cinematic realism. CAMERA: 85mm, f/2.8, ISO 200, 1/160s. Focus on face/torso. Shallow depth of field, natural bokeh."
B4 = "BLOCK 4 (Rendering & Output): RENDERING: Subsurface Scattering, Global Illumination, Fresnel, Frequency separation on skin. Watermark: 'feat. Valeria Cross 👠' (elegant cursive, champagne, bottom center/left, opacity 90%, very small font size)."
NEG = "NEGATIVE PROMPTS: [Face] female/young face, smooth skin, distortion. [Hair] long/medium hair, ponytail, bun, braid. [Body] body/chest/leg hair (peli NO!)."

# --- STATO UTENTE ---
user_settings = {}

def get_settings(cid):
    if cid not in user_settings:
        user_settings[cid] = {'ratio': '2:3', 'count': 1}
    return user_settings[cid]

# --- TASTIERE ---
def get_formato_keyboard(cid):
    current = get_settings(cid)
    markup = InlineKeyboardMarkup()
    riga1 = ["2:3", "3:4", "4:5", "9:16", "2:1"]
    riga2 = ["3:2", "4:3", "5:4", "16:9", "3:1"]
    btns_riga1 = [InlineKeyboardButton(f"✅ {r}" if current['ratio'] == r else r, callback_data=f"ar_{r}") for r in riga1]
    btns_riga2 = [InlineKeyboardButton(f"✅ {r}" if current['ratio'] == r else r, callback_data=f"ar_{r}") for r in riga2]
    markup.row(*btns_riga1)
    markup.row(*btns_riga2)
    return markup

def get_settings_keyboard(cid):
    current = get_settings(cid)
    markup = InlineKeyboardMarkup()
    counts = [1, 2, 3, 4]
    btns_counts = [InlineKeyboardButton(f"✅ {c}" if current['count'] == c else str(c), callback_data=f"n_{c}") for c in counts]
    markup.row(*btns_counts)
    return markup

# --- COMANDI MENU ---
@bot.message_handler(commands=['start', 'reset'])
def start(m):
    cid = m.chat.id
    user_settings[cid] = {'ratio': '2:3', 'count': 1}
    bot.send_message(cid, f"<b>👠 CLOSET v{VERSION} Online</b>\nImpostazioni resettate ai default (Formato: 2:3, Foto: 1).\nUsa /formato o /settings per personalizzare.")

@bot.message_handler(commands=['formato'])
def menu_formato(m):
    bot.send_message(m.chat.id, "📐 <b>Scegli il Formato (Aspect Ratio)</b>", reply_markup=get_formato_keyboard(m.chat.id))

@bot.message_handler(commands=['settings'])
def menu_settings(m):
    bot.send_message(m.chat.id, "🖼️ <b>Scegli il Numero di Foto</b>", reply_markup=get_settings_keyboard(m.chat.id))

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    data = call.data
    current = get_settings(cid)
    
    if data.startswith("ar_"):
        current['ratio'] = data.split("_")[1]
        bot.answer_callback_query(call.id, f"Formato: {current['ratio']}")
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=get_formato_keyboard(cid))
    elif data.startswith("n_"):
        current['count'] = int(data.split("_")[1])
        bot.answer_callback_query(call.id, f"Foto: {current['count']}")
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=get_settings_keyboard(cid))

# --- GENERAZIONE ---
@bot.message_handler(func=lambda m: not m.text.startswith('/'))
def generate_closet(m):
    cid = m.chat.id
    idea = m.text
    settings = get_settings(cid)
    
    wait = bot.send_message(cid, "🧠 <b>Sintesi prompt...</b>")
    
    instruction = (
        f"Convert this idea into a concise list of visual keywords for an image generator: '{idea}'. "
        f"Focus ONLY on clothes, lighting, and environment. NO narrative, NO verbs, NO full sentences. "
        f"Just comma-separated tags. Max 30 words. English only."
    )

    try:
        # 1. Sintesi testo
        response_text = client.models.generate_content(model="gemini-2.0-flash", contents=[instruction])
        scena_keywords = response_text.text.strip()
        
        final_prompt = f"{B1}\n\n{B2}\n\n{B3}\n\nSCENE: {scena_keywords}\nFORMAT: {settings['ratio']}\n\n{B4}\n\nNEGATIVE PROMPTS: {NEG}"
        
        bot.edit_message_text(f"🎨 <b>Scatto in corso (Nano Banana Pro)</b>\nFormato: {settings['ratio']} | Foto: {settings['count']}", cid, wait.message_id)
        
        # 2. Prepara i contenuti (Testo + Immagine Faccia)
        api_contents = [final_prompt]
        if MASTER_PART:
            api_contents.append(MASTER_PART)
        
        # 3. Generazione Immagine
        for i in range(settings['count']):
            response_img = client.models.generate_content(
                model="nano-banana-pro-preview",
                contents=api_contents,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    safety_settings=[{"category": c, "threshold": "BLOCK_NONE"} for c in 
                                     ["HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_HATE_SPEECH", 
                                      "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
                )
            )
            
            candidate = response_img.candidates[0]
            for part in candidate.content.parts:
                if part.inline_data:
                    image_stream = BytesIO(part.inline_data.data)
                    bot.send_photo(cid, image_stream, caption=f"<code>{html.escape(scena_keywords)}</code>")
                    break
                    
        bot.delete_message(cid, wait.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Errore API: {str(e)}", cid, wait.message_id)

# --- SERVER KOYEB ---
app = flask.Flask(__name__)
@app.route('/')
def health(): return "CLOSET_OK"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
