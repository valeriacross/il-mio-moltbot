# ---------------------------------------------------------
# VERSION: V3.10 (Quota Optimized - Nano Banana Engine)
# TIMESTAMP: 2026-02-16 08:15 WET
# CHANGELOG:
# - ENGINE SWAP: Updated to models/gemini-2.5-flash-preview-image 
#   for higher RPD quota as per user screenshot.
# - VISION SWAP: Updated to models/gemini-3-flash for faster analysis.
# - RETAINED: All Block 1-4 Master Prompt directives.
# ---------------------------------------------------------

import os, io, threading, logging, flask, telebot, re
from telebot import types
from google import genai
from google.genai import types as genai_types
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("CLOSET_TOKEN")
API_KEY = os.environ.get("GOOGLE_API_KEY")

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- MODELLI (Aggiornati da Screenshot AI Studio) ---
VISION_MODEL = "models/gemini-3-flash"
GEN_MODEL = "models/gemini-2.5-flash-preview-image"

executor = ThreadPoolExecutor(max_workers=8)
user_ar = defaultdict(lambda: "2:3")
user_qty = defaultdict(lambda: 2)
original_outfit_analysis = {}

# --- THE VOGUE SHIELD ---
def vogue_sanitize(text):
    if not text: return ""
    euphemisms = {
        r"\b(bra|reggiseno|soutien|sutiã)\b": "luxury couture bralette",
        r"\b(underwear|mutande|panties|calcinha|cueca)\b": "intimate silk apparel",
        r"\b(thong|perizoma|fio dental)\b": "minimalist high-fashion bottom",
        r"\b(nude|nudo|nu|nua)\b": "natural skin texture",
        r"\b(cleavage|scollatura|decote)\b": "glamorous decolletage",
        r"\b(breast|seno|seios|peito)\b": "feminine torso silhouette (cup D)",
        r"\b(butt|booty|culo|bumbum|rabo)\b": "lower silhouette",
        r"\b(see-through|trasparente|transparente)\b": "sheer translucent fabric",
        r"\b(sexy|hot|quente|seducente)\b": "alluring and sophisticated",
        r"\b(bikini|costume)\b": "Vogue-style swimwear",
    }
    sanitized = text.lower()
    for pattern, replacement in euphemisms.items():
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized.capitalize()

# --- MENU SETTINGS (No 1:1) ---
def get_settings_markup(uid):
    markup = types.InlineKeyboardMarkup(row_width=3)
    ar_buttons = [
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='2:3' else ''}2:3", callback_data="set_ar_2:3"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='3:2' else ''}3:2", callback_data="set_ar_3:2"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='9:16' else ''}9:16", callback_data="set_ar_9:16"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='16:9' else ''}16:9", callback_data="set_ar_16:9"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='4:5' else ''}4:5", callback_data="set_ar_4:5")
    ]
    qty_buttons = [
        types.InlineKeyboardButton(f"{'✅ ' if user_qty[uid]==1 else ''}1 Foto", callback_data="set_qty_1"),
        types.InlineKeyboardButton(f"{'✅ ' if user_qty[uid]==2 else ''}2 Foto", callback_data="set_qty_2"),
        types.InlineKeyboardButton(f"{'✅ ' if user_qty[uid]==4 else ''}4 Foto", callback_data="set_qty_4")
    ]
    markup.add(*ar_buttons)
    markup.add(*qty_buttons)
    return markup

# --- CORE FUNCTIONS ---
def analyze_outfit_vision(img_bytes):
    try:
        prompt = "Analyze outfit materials, lighting direction, and background location. Max 50 words."
        response = client.models.generate_content(model=VISION_MODEL, 
            contents=[prompt, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")])
        return response.text if response.text else "High-fashion editorial garment."
    except: return "Editorial fashion outfit."

def generate_closet_task_v3(img_bytes, ar_scelto, user_notes, vision_desc, mode="standard"):
    try:
        if not os.path.exists("master_face.png"): return None, "ERRORE: master_face.png mancante!"
        with open("master_face.png", "rb") as f:
            face_part = genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
        
        safe_outfit = vogue_sanitize(vision_desc)
        safe_notes = vogue_sanitize(user_notes)
        
        system_prompt = f"""
        [BLOCCO 1: IDENTITY PRIORITY]
        Identity Priority: ABSOLUTE. Reference image (master_face.png) is the ONLY source for the face. 
        Zero face drift.

        [BLOCCO 2: SUBJECT SPECIFICATIONS]
        Subject: Nameless Italian transmasculine avatar. 
        Body: Feminine soft hourglass, prosperous breasts (CUP D), 180cm, 85kg. 
        Skin: COMPLETELY HAIRLESS (arms, legs, chest, breasts — hair NO!).
        Face: Male Italian, ~60 years old. Oval-rectangular. Ultra-detailed skin (pores, wrinkles, bags).
        Expression: Calm half-smile, NO teeth. Eyes: Dark brown/green.
        Beard: Light grey/silver, groomed, 6-7 cm. 
        Glasses: MANDATORY thin octagonal Vogue, Havana dark (NEVER removed).

        [BLOCCO 3: HAIR & TECHNICAL]
        Hair: Light grey/silver. Short elegant Italian style, volume. Sides 1-2 cm, nape exposed. Top <15cm. 
        Hair NEVER touching neck, shoulders, or clavicles.
        Technical: 85mm, f/2.8, ISO 200, cinematic realism. Focus on face/torso. Bokeh naturale.
        Rendering: Subsurface Scattering, Global Illumination, Fresnel, Frequency separation on skin.

        [BLOCCO 4: OUTPUT CONTROL]
        Anti-Faceswap: Do NOT collage. Generate native pixels. 
        Watermark: "feat. Valeria Cross 👠" (elegant cursive, very small scale, champagne color, bottom left, 80% opacity).
        Format: {ar_scelto}.

        PROMPT: {safe_notes}
        SCENE ANALYSIS: {safe_outfit}

        NEGATIVE PROMPT:
        female face, young features, smooth skin, hair touching shoulders, body hair, peli NO!, bad faceswap, pasted face.
        """

        response = client.models.generate_content(
            model=GEN_MODEL,
            contents=[system_prompt, face_part, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")],
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                safety_settings=[{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            )
        )

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data: return part.inline_data.data, None
        
        reason = response.candidates[0].finish_reason if response.candidates else "EMPTY"
        return None, f"Fallito: {reason}"

    except Exception as e: return None, str(e)

# --- HANDLERS ---
@bot.message_handler(commands=['start', 'settings'])
def show_settings(m):
    bot.send_message(m.chat.id, "<b>👠 Valeria Closet V3.1 (Nano Banana)</b>\nQuota ottimizzata. Motore Flash Image attivo.", 
                     reply_markup=get_settings_markup(m.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def handle_settings_cb(call):
    uid = call.from_user.id
    if "ar_" in call.data: user_ar[uid] = call.data.replace("set_ar_", "")
    elif "qty_" in call.data: user_qty[uid] = int(call.data.replace("set_qty_", ""))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_settings_markup(uid))

@bot.message_handler(content_types=['photo'])
def handle_new_photo(m):
    uid = m.from_user.id
    qty, fmt = user_qty[uid], user_ar[uid]
    img_bytes = bot.download_file(bot.get_file(m.photo[-1].file_id).file_path)
    
    bot.reply_to(m, f"⚡ Rendering V3.1 (Nano Banana Engine)...")
    vision_desc = analyze_outfit_vision(img_bytes)
    original_outfit_analysis[uid] = vision_desc
    bot.send_message(m.chat.id, f"📝 <b>Vision 3.1:</b> <i>{vogue_sanitize(vision_desc)}</i>")
    
    for i in range(qty):
        def run(idx):
            res, err = generate_closet_task_v3(img_bytes, fmt, m.caption or "", vision_desc)
            if res: bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"v31_{idx+1:02d}.jpg")
            else: bot.send_message(m.chat.id, f"❌ {err}")
        executor.submit(run, i)

app = flask.Flask(__name__)
@app.route('/')
def h(): return "V3.1 Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
