# ---------------------------------------------------------
# VERSION: V3.00 (The Rendering Master)
# TIMESTAMP: 2026-02-15
# CHANGELOG:
# - INTEGRATED MASTER PROMPTS (BLOCCO 1-4)
# - ADVANCED LIGHTING MATCHING (Vision 2.0)
# - NO 1:1 RATIO (As per user preference)
# - ANTI-COLLAGE NATIVE RENDERING
# ---------------------------------------------------------

import os, io, threading, logging, flask, telebot, re
from telebot import types
from google import genai
from google.genai import types as genai_types
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- LOGGING & CONFIG ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("CLOSET_TOKEN")
API_KEY = os.environ.get("GOOGLE_API_KEY")

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- ENGINE CONFIG ---
VISION_MODEL = "models/gemini-2.0-flash" 
GEN_MODEL = "models/gemini-2.0-flash" 

executor = ThreadPoolExecutor(max_workers=10)
user_ar = defaultdict(lambda: "2:3")
user_qty = defaultdict(lambda: 2)
original_outfit_analysis = {}

# --- THE VOGUE SHIELD (Sanitizzazione Avanzata) ---
def vogue_sanitize(text):
    if not text: return ""
    euphemisms = {
        r"\b(bra|reggiseno|soutien|sutiã)\b": "luxury couture bralette",
        r"\b(underwear|mutande|panties|calcinha|cueca)\b": "intimate silk apparel",
        r"\b(thong|perizoma|fio dental)\b": "minimalist high-fashion bottom",
        r"\b(nude|nudo|nu|nua)\b": "natural hyper-realistic skin texture",
        r"\b(cleavage|scollatura|decote)\b": "glamorous decolletage",
        r"\b(breast|seno|seios|peito)\b": "feminine torso silhouette (cup D)",
        r"\b(butt|booty|culo|bumbum|rabo)\b": "lower silhouette curves",
        r"\b(see-through|trasparente|transparente)\b": "sheer translucent luxury fabric",
        r"\b(sexy|hot|quente|seducente)\b": "alluring, sophisticated and editorial",
        r"\b(bikini|costume)\b": "Vogue-style swimwear",
        r"\b(peli|pelo|hair on body)\b": "completely smooth hairless skin"
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
        types.InlineKeyboardButton(f"{'✅ ' if user_qty[uid]==1 else ''}1 Scatto", callback_data="set_qty_1"),
        types.InlineKeyboardButton(f"{'✅ ' if user_qty[uid]==2 else ''}2 Scatti", callback_data="set_qty_2"),
        types.InlineKeyboardButton(f"{'✅ ' if user_qty[uid]==4 else ''}4 Scatti", callback_data="set_qty_4")
    ]
    markup.add(*ar_buttons)
    markup.add(*qty_buttons)
    return markup

# --- ANALISI VISIONE 3.0 ---
def analyze_scene_vision(img_bytes):
    try:
        prompt = """
        Technical Analysis for Photorealistic Rendering:
        1. OUTFIT: Describe technical materials (silk, leather, wool), cut, and precise color palette.
        2. LIGHTING: Identify light source direction, intensity, and color temperature (e.g., 3000K warm side light).
        3. PHYSICS: Describe the environment (interior/exterior) and how light interacts with the subject.
        Return a concise technical brief (max 60 words).
        """
        response = client.models.generate_content(model=VISION_MODEL, 
            contents=[prompt, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")])
        return response.text if response.text else "Neutral studio lighting, editorial high-fashion."
    except: return "High-fashion editorial setting."

# --- GENERAZIONE MASTER (BLOCCHI 1-4 INTEGRATI) ---
def generate_closet_v3(img_bytes, ar_scelto, user_notes, vision_desc, mode="standard"):
    try:
        if not os.path.exists("master_face.png"): return None, "Manca master_face.png"
        with open("master_face.png", "rb") as f:
            face_part = genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
        
        safe_outfit = vogue_sanitize(vision_desc)
        safe_notes = vogue_sanitize(user_notes)
        
        # LOGICA V2.0 (Rigenerazione da zero)
        is_v2 = "v2.0" in user_notes.lower() or mode == "v2.0"
        mode_directive = ""
        if is_v2:
            mode_directive = "DISCARD ORIGINAL PIXELS. Generate a NEW scene from scratch inspired only by the concept."
        else:
            mode_directive = f"MATCH SCENE PHYSICS: Integrate subject into the lighting environment described: {safe_outfit}."

        system_prompt = f"""
        [BLOCCO 1: ATTIVAZIONE]
        Identity Priority: ABSOLUTE. Reference image (master_face.png) is the ONLY source for the face.
        ZERO face drift. 

        [BLOCCO 2: SOGGETTO & VISO]
        Subject: Nameless Italian transmasculine avatar.
        Body: Feminine soft hourglass, prosperous breasts (CUP D), 180cm, 85kg.
        Skin: COMPLETELY HAIRLESS (Arms, legs, chest, breasts — NO PELI!).
        Face (INVARIABLE): Male Italian, 60 years old. Oval-rectangular. Ultra-detailed skin (pores, wrinkles, bags).
        Expression: Calm half-smile, NO teeth. Eyes: dark brown/green.
        Beard: Light grey/silver, groomed, 6-7 cm.
        Glasses: MANDATORY thin octagonal Vogue, Havana dark (NEVER removed).

        [BLOCCO 3: CAPELLI & TECNICA]
        Hair: Light grey/silver. Short elegant Italian style. Sides 1-2cm, nape exposed. Top <15cm. 
        NEVER touching neck, shoulders, or clavicles.
        Technical: 85mm, f/2.8, ISO 200, cinematic realism, natural bokeh.
        Rendering: Subsurface Scattering, Global Illumination, Fresnel, Frequency separation on skin.

        [BLOCCO 4: OUTPUT CONTROL]
        Anti-Faceswap: Do NOT collage. Generate native pixels. 
        Lighting: {safe_outfit}. Directional light must hit the male face and female body consistently.
        Watermark: "feat. Valeria Cross 👠" (elegant cursive, champagne, bottom left, 90% opacity).
        Format: {ar_scelto}.
        
        Notes: {safe_notes}
        {mode_directive}

        [NEGATIVE PROMPTS]
        female face, young features, smooth face, distortions, long hair, ponytail, hair touching shoulders, body hair, peli, chest hair, low quality, collage, pasted edges.
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
        return None, "Generazione fallita (Safety o Timeout)"
    except Exception as e: return None, str(e)

# --- TELEGRAM HANDLERS ---
@bot.message_handler(commands=['start', 'settings'])
def start(m):
    bot.send_message(m.chat.id, "<b>👠 Valeria Closet V3.0 (Rendering Master)</b>\nMotore Flash attivo. Formato 1:1 disabilitato.", 
                     reply_markup=get_settings_markup(m.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def settings_cb(call):
    uid = call.from_user.id
    if "ar_" in call.data: user_ar[uid] = call.data.replace("set_ar_", "")
    elif "qty_" in call.data: user_qty[uid] = int(call.data.replace("set_qty_", ""))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_settings_markup(uid))

@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    uid = m.from_user.id
    img_bytes = bot.download_file(bot.get_file(m.photo[-1].file_id).file_path)
    
    msg = bot.reply_to(m, "🔍 <i>Analisi scena e luce in corso...</i>")
    vision_desc = analyze_scene_vision(img_bytes)
    original_outfit_analysis[uid] = vision_desc
    
    bot.edit_message_text(f"📸 <b>Vision 3.0:</b> <i>{vogue_sanitize(vision_desc)}</i>", m.chat.id, msg.message_id)
    
    for i in range(user_qty[uid]):
        def task(idx):
            res, err = generate_closet_v3(img_bytes, user_ar[uid], m.caption or "", vision_desc)
            if res: bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"valeria_{idx+1}.jpg")
            else: bot.send_message(m.chat.id, f"❌ Errore scatto {idx+1}: {err}")
        executor.submit(task, i)

@bot.message_handler(func=lambda m: m.reply_to_message and m.text)
def handle_reply(m):
    # Supporto per comando "V2.0" o modifiche testuali
    uid = m.from_user.id
    target = m.reply_to_message
    file_id = target.document.file_id if target.document else (target.photo[-1].file_id if target.photo else None)
    
    if file_id:
        img_bytes = bot.download_file(bot.get_file(file_id).file_path)
        vision_context = original_outfit_analysis.get(uid, "Fashion ensemble.")
        mode = "v2.0" if "v2.0" in m.text.lower() else "standard"
        
        bot.reply_to(m, f"🔄 {'Rigenerazione Totale (V2.0)' if mode=='v2.0' else 'Editing'}...")
        executor.submit(lambda: (
            res := generate_closet_v3(img_bytes, user_ar[uid], m.text, vision_context, mode=mode),
            bot.send_document(m.chat.id, io.BytesIO(res[0]), visible_file_name="v3_edit.jpg") if res[0] else bot.send_message(m.chat.id, f"❌ {res[1]}")
        ))

app = flask.Flask(__name__)
@app.route('/')
def h(): return "V3.0 Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
