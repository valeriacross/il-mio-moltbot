# ---------------------------------------------------------
# VERSION: V3.2.1 (Koyeb & v1beta - Nano Banana Pro)
# TIMESTAMP: 2026-02-16
# PLATFORM: Koyeb (Eco/Starter Instance)
# FIX: Model name 'nano-banana-pro-preview' + Dynamic Msg
# ---------------------------------------------------------

import os, io, threading, logging, flask, telebot, re
from telebot import types
from google import genai
from google.genai import types as genai_types
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAZIONE & LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("CLOSET_TOKEN")
API_KEY = os.environ.get("GOOGLE_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

# --- CLIENT FORZATO SU v1beta ---
client = genai.Client(
    api_key=API_KEY, 
    http_options={'api_version': 'v1beta'}
)

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- MODELLI (Configurazione confermata funzionante) ---
VISION_MODEL = "gemini-1.5-flash"
GEN_MODEL = "nano-banana-pro-preview"

executor = ThreadPoolExecutor(max_workers=8)
user_ar = defaultdict(lambda: "2:3")
user_qty = defaultdict(lambda: 2)

# --- VOGUE SHIELD (Sanitizzazione V3.2) ---
def vogue_sanitize(text):
    if not text: return ""
    euphemisms = {
        r"\b(bikini|costume|due pezzi)\b": "architectural technical silk ensemble",
        r"\b(bra|reggiseno|top)\b": "structured technical couture bodice",
        r"\b(slip|mutanda|bottom)\b": "high-fashion minimalist silhouette",
        r"\b(nude|nudo|naked)\b": "natural hyper-realistic skin texture",
        r"\b(breast|seno|seios)\b": "feminine torso silhouette (cup D)",
        r"\b(peli|pelo|hair on body)\b": "completely smooth hairless skin"
    }
    sanitized = text.lower()
    for pattern, replacement in euphemisms.items():
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized.capitalize()

# --- ANALISI VISIONE ---
def analyze_outfit_vision(img_bytes):
    try:
        prompt = "Describe outfit materials, cut, and lighting. Max 30 words."
        response = client.models.generate_content(
            model=VISION_MODEL, 
            contents=[prompt, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")]
        )
        return response.text if response.text else "High-fashion editorial garment."
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return "Editorial fashion outfit."

# --- GENERAZIONE VALERIA ---
def generate_closet_task_v32(img_bytes, ar_scelto, user_notes, vision_desc):
    try:
        if not os.path.exists("master_face.png"):
            return None, "ERRORE: master_face.png non trovato nel repo!"
        
        with open("master_face.png", "rb") as f:
            face_part = genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
        
        system_prompt = f"""
        [IDENTITY] Master_face.png is MANDATORY. Male Italian face, ~60yo, silver beard 7cm, octagonal Havana glasses.
        [BODY] Feminine hourglass, Cup D, 180cm, 85kg, hairless skin.
        [TECH] 8K resolution, 85mm f/2.8, Cinematic Lighting, Subsurface Scattering.
        [CONTEXT] {vogue_sanitize(vision_desc)}. User Notes: {vogue_sanitize(user_notes)}.
        [RULES] NO faceswap/collage. Generate native pixels. 
        Watermark: "feat. Valeria Cross 👠" (small, champagne, bottom left).
        Format: {ar_scelto}.
        """

        response = client.models.generate_content(
            model=GEN_MODEL,
            contents=[
                system_prompt, 
                face_part, 
                genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            ],
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                safety_settings=[{"category": c, "threshold": "BLOCK_NONE"} for c in [
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT", 
                    "HARM_CATEGORY_HATE_SPEECH", 
                    "HARM_CATEGORY_HARASSMENT", 
                    "HARM_CATEGORY_DANGEROUS_CONTENT"
                ]]
            )
        )

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data: return part.inline_data.data, None
        
        reason = response.candidates[0].finish_reason if response.candidates else "NO_CANDIDATE"
        return None, f"Status: {reason}"

    except Exception as e:
        return None, f"System Error: {str(e)}"

# --- BOT HANDLERS ---
@bot.message_handler(commands=['start', 'settings'])
def show_settings(m):
    markup = types.InlineKeyboardMarkup(row_width=3)
    ar_buttons = [types.InlineKeyboardButton(f"{'✅ ' if user_ar[m.from_user.id]==ar else ''}{ar}", callback_data=f"set_ar_{ar}") for ar in ["2:3", "9:16", "4:5"]]
    qty_buttons = [types.InlineKeyboardButton(f"{'✅ ' if user_qty[m.from_user.id]==q else ''}{q} Foto", callback_data=f"set_qty_{q}") for q in [1, 2, 4]]
    markup.add(*ar_buttons)
    markup.add(*qty_buttons)
    bot.send_message(m.chat.id, "<b>👠 Valeria Closet V3.2.1 (Koyeb)</b>\nEngine: Nano Banana Pro (v1beta)", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def handle_settings_cb(call):
    uid = call.from_user.id
    if "ar_" in call.data: user_ar[uid] = call.data.replace("set_ar_", "")
    elif "qty_" in call.data: user_qty[uid] = int(call.data.replace("set_qty_", ""))
    bot.answer_callback_query(call.id, "Configurazione aggiornata!")

@bot.message_handler(content_types=['photo'])
def handle_new_photo(m):
    uid = m.from_user.id
    qty, fmt = user_qty[uid], user_ar[uid]
    
    img_bytes = bot.download_file(bot.get_file(m.photo[-1].file_id).file_path)
    
    # Messaggio dinamico richiesto
    bot.reply_to(m, f"⚡ Analisi e Rendering in corso (v1beta)...\n📸 Attese: {qty} foto | Formato: {fmt}")
    
    vision_desc = analyze_outfit_vision(img_bytes)
    
    for i in range(qty):
        def run(idx):
            res, err = generate_closet_task_v32(img_bytes, fmt, m.caption or "", vision_desc)
            if res: bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"valeria_{idx+1}.jpg")
            else: bot.send_message(m.chat.id, f"❌ {err}")
        executor.submit(run, i)

# --- FLASK SERVER PER KOYEB ---
app = flask.Flask(__name__)
@app.route('/')
def health(): return "Healthy"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    bot.infinity_polling()
    
