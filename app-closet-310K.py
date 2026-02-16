# ---------------------------------------------------------
# VERSION: V3.10 (Koyeb Edition - Nano Banana)
# TIMESTAMP: 2026-02-16
# PLATFORM: Koyeb (Eco/Nano Instance)
# MODELS: 
# - Vision: gemini-3-flash (Fast Analysis)
# - Gen: gemini-2.5-flash-preview-image (High Quota 500 RPM)
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

# Recupero variabili d'ambiente (impostate su Koyeb)
TOKEN = os.environ.get("CLOSET_TOKEN")
API_KEY = os.environ.get("GOOGLE_API_KEY")
# Koyeb assegna una porta dinamica, la leggiamo qui (default 10000)
PORT = int(os.environ.get("PORT", 10000))

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- MOTORI AD ALTA QUOTA (500 RPM) ---
VISION_MODEL = "models/gemini-3-flash"
GEN_MODEL = "models/gemini-2.5-flash-preview-image"

executor = ThreadPoolExecutor(max_workers=8)
user_ar = defaultdict(lambda: "2:3")
user_qty = defaultdict(lambda: 2)
original_outfit_analysis = {}

# --- VOGUE SHIELD (Sanitizzazione Aggressiva V3.1) ---
def vogue_sanitize(text):
    if not text: return ""
    euphemisms = {
        # REPARTO "RISCHIO" RIDEFINITO TECNICAMENTE
        r"\b(bikini|costume|swimwear|due pezzi)\b": "layered architectural technical silk two-piece ensemble",
        r"\b(bra|reggiseno|soutien|top)\b": "structured sculpted bodice in technical fabric",
        r"\b(slip|mutanda|panties|bottom)\b": "high-cut minimalist silhouette technical bottom",
        r"\b(thong|perizoma|fio dental)\b": "ultra-minimalist technical couture structure",
        # EUFEMISMI STANDARD
        r"\b(underwear|intimo|lingerie)\b": "layered technical base garments",
        r"\b(nude|nudo|nu|nua|naked)\b": "natural hyper-realistic skin texture study",
        r"\b(breast|seno|seios|peito)\b": "feminine torso silhouette (cup D volume)",
        r"\b(peli|pelo|hair on body)\b": "completely smooth hairless polished skin"
    }
    sanitized = text.lower()
    for pattern, replacement in euphemisms.items():
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized.capitalize()

# --- ANALISI VISIONE (Veloce) ---
def analyze_outfit_vision(img_bytes):
    try:
        prompt = "Technical Analysis: Describe outfit materials, cut, and lighting direction. Max 40 words."
        response = client.models.generate_content(model=VISION_MODEL, 
            contents=[prompt, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")])
        return response.text if response.text else "High-fashion editorial garment."
    except: return "Editorial fashion outfit."

# --- GENERAZIONE MASTER (Nano Banana) ---
def generate_closet_task_v3(img_bytes, ar_scelto, user_notes, vision_desc):
    try:
        if not os.path.exists("master_face.png"): return None, "ERRORE: master_face.png mancante nel repo!"
        
        with open("master_face.png", "rb") as f:
            face_part = genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
        
        safe_outfit = vogue_sanitize(vision_desc)
        safe_notes = vogue_sanitize(user_notes)
        
        system_prompt = f"""
        [IDENTITY - MANDATORY]
        Reference image (master_face.png) is the ABSOLUTE source for the face.
        Face: Male Italian, ~60 years old. Oval-rectangular. Ultra-detailed skin.
        Beard: Light grey/silver, groomed, 7 cm. 
        Glasses: MANDATORY thin octagonal Vogue, Havana dark (NEVER removed).

        [BODY & SKIN]
        Body: Feminine soft hourglass, prosperous breasts (CUP D), 180cm, 85kg. 
        Skin: COMPLETELY HAIRLESS (arms, legs, chest, breasts — hair NO!).
        Rendering: Subsurface Scattering, Global Illumination, Fresnel.

        [SCENE & OUTFIT]
        Scene Context: {safe_outfit}
        User Request: {safe_notes}
        
        [OUTPUT RULES]
        Anti-Faceswap: Do NOT just paste the face. Generate native pixels with consistent lighting.
        Watermark: "feat. Valeria Cross 👠" (small, champagne, bottom left, 80% opacity).
        Format: {ar_scelto}.
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
        
        # Diagnostica per Koyeb logs
        reason = response.candidates[0].finish_reason if response.candidates else "EMPTY_RESPONSE"
        return None, f"Fallito: {reason}"

    except Exception as e: return None, str(e)

# --- TELEGRAM HANDLERS ---
@bot.message_handler(commands=['start', 'settings'])
def show_settings(m):
    markup = types.InlineKeyboardMarkup(row_width=3)
    ar_buttons = [
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[m.from_user.id]=='2:3' else ''}2:3", callback_data="set_ar_2:3"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[m.from_user.id]=='9:16' else ''}9:16", callback_data="set_ar_9:16"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[m.from_user.id]=='4:5' else ''}4:5", callback_data="set_ar_4:5")
    ]
    qty_buttons = [
        types.InlineKeyboardButton(f"{'✅ ' if user_qty[m.from_user.id]==1 else ''}1 Foto", callback_data="set_qty_1"),
        types.InlineKeyboardButton(f"{'✅ ' if user_qty[m.from_user.id]==2 else ''}2 Foto", callback_data="set_qty_2"),
        types.InlineKeyboardButton(f"{'✅ ' if user_qty[m.from_user.id]==4 else ''}4 Foto", callback_data="set_qty_4")
    ]
    markup.add(*ar_buttons)
    markup.add(*qty_buttons)
    bot.send_message(m.chat.id, "<b>👠 Valeria Closet V3.1 (Koyeb)</b>\nQuota ottimizzata. Motore Nano Banana attivo.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def handle_settings_cb(call):
    uid = call.from_user.id
    if "ar_" in call.data: user_ar[uid] = call.data.replace("set_ar_", "")
    elif "qty_" in call.data: user_qty[uid] = int(call.data.replace("set_qty_", ""))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=show_settings(call.message)) # Fix refresh
    bot.answer_callback_query(call.id, "Salvato!")

@bot.message_handler(content_types=['photo'])
def handle_new_photo(m):
    uid = m.from_user.id
    qty, fmt = user_qty[uid], user_ar[uid]
    img_bytes = bot.download_file(bot.get_file(m.photo[-1].file_id).file_path)
    
    bot.reply_to(m, f"⚡ Rendering Nano Banana ({qty} scatti)...")
    vision_desc = analyze_outfit_vision(img_bytes)
    
    for i in range(qty):
        def run(idx):
            res, err = generate_closet_task_v3(img_bytes, fmt, m.caption or "", vision_desc)
            if res: bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"v31_{idx+1}.jpg")
            else: bot.send_message(m.chat.id, f"❌ {err}")
        executor.submit(run, i)

# --- WEB SERVER PER KOYEB HEALTH CHECK ---
app = flask.Flask(__name__)
@app.route('/')
def health(): return "Koyeb Service is Healthy (V3.1)"

if __name__ == "__main__":
    # Avvia il server Flask sulla porta specificata da Koyeb
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    bot.infinity_polling()
