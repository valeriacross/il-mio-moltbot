# ---------------------------------------------------------
# VERSION: V2.30 (The Flash Switch)
# TIMESTAMP: 2026-02-15 08:10 WET
# CHANGELOG:
# - ENGINE SWAP: Switched GEN_MODEL to 'models/gemini-2.0-flash' 
#   (High Quota: 2000 RPD vs 250 RPD of Pro).
# - PROMPT HARDENING: Adjusted instructions for the Flash model to 
#   prevent "cut-and-paste" faceswaps, forcing full regeneration.
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

# --- MODELLI ---
VISION_MODEL = "models/gemini-2.0-flash" # Visione rapida
# MOTORE CAMBIATO: Usiamo il Flash (2000 richieste/giorno)
GEN_MODEL = "models/gemini-2.0-flash" 

executor = ThreadPoolExecutor(max_workers=8)
user_ar = defaultdict(lambda: "2:3")
user_qty = defaultdict(lambda: 2)
original_outfit_analysis = {}

# --- THE VOGUE SHIELD ---
def vogue_sanitize(text):
    if not text: return ""
    euphemisms = {
        r"\b(bra|reggiseno|soutien|sutiã)\b": "luxury bralette",
        r"\b(underwear|mutande|panties|calcinha|cueca)\b": "intimate silk apparel",
        r"\b(thong|perizoma|fio dental)\b": "minimalist couture bottom",
        r"\b(nude|nudo|nu|nua)\b": "natural skin texture",
        r"\b(cleavage|scollatura|decote)\b": "glamorous decolletage",
        r"\b(breast|seno|seios|peito)\b": "feminine torso silhouette",
        r"\b(butt|booty|culo|bumbum|rabo)\b": "lower silhouette",
        r"\b(see-through|trasparente|transparente)\b": "sheer translucent fabric",
        r"\b(sexy|hot|quente|seducente)\b": "alluring and sophisticated",
        r"\b(bikini|costume)\b": "high-fashion swimwear",
    }
    sanitized = text.lower()
    for pattern, replacement in euphemisms.items():
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized.capitalize()

# --- MENU SETTINGS ---
def get_settings_markup(uid):
    markup = types.InlineKeyboardMarkup(row_width=3)
    ar_buttons = [
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='2:3' else ''}2:3", callback_data="set_ar_2:3"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='3:2' else ''}3:2", callback_data="set_ar_3:2"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='9:16' else ''}9:16", callback_data="set_ar_9:16"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='16:9' else ''}16:9", callback_data="set_ar_16:9"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='1:1' else ''}1:1", callback_data="set_ar_1:1"),
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

@bot.message_handler(commands=['start', 'settings'])
def show_settings(m):
    bot.send_message(m.chat.id, "<b>👗 Valeria Closet V2.30 (Flash Engine)</b>\nScegli il formato e il numero di scatti:", 
                     reply_markup=get_settings_markup(m.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def handle_settings_cb(call):
    uid = call.from_user.id
    if "ar_" in call.data: user_ar[uid] = call.data.replace("set_ar_", "")
    elif "qty_" in call.data: user_qty[uid] = int(call.data.replace("set_qty_", ""))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_settings_markup(uid))
    bot.answer_callback_query(call.id, "Impostazioni aggiornate")

# --- CORE FUNCTIONS ---
def analyze_outfit_vision(img_bytes):
    try:
        # Prompt semplificato per Flash per evitare confusione
        prompt = """
        Analyze image in 2 parts.
        1. OUTFIT: Detailed technical description (materials, colors, cut).
        2. CONTEXT: Is it a studio background or a real location (beach, snow, street)? 
        If real, describe the location and lighting.
        Max 50 words.
        """
        response = client.models.generate_content(model=VISION_MODEL, 
            contents=[prompt, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")])
        return response.text if response.text else "High-fashion technical garment."
    except: return "Editorial fashion outfit."

def generate_closet_task(img_bytes, ar_scelto, user_notes, vision_desc, edit_mode=False):
    try:
        if not os.path.exists("master_face.png"): return None, "ERRORE: master_face.png mancante!"
        
        with open("master_face.png", "rb") as f:
            face_part = genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
        
        safe_outfit = vogue_sanitize(vision_desc)
        safe_notes = vogue_sanitize(user_notes)
        
        mode_instruction = ""
        if edit_mode:
            mode_instruction = f"""
            MODIFICA QUESTA IMMAGINE: {safe_notes}.
            Non incollare elementi. Rigenera l'immagine mantenendo l'ensemble ma applicando la modifica.
            """
        else:
            mode_instruction = "Genera un'immagine COMPLETAMENTE NUOVA ispirata all'immagine di riferimento."

        system_prompt = f"""
        OUTFIT 👗
        {mode_instruction}
        Foto alta moda 8K, illuminazione professionale.

        IL SOGGETTO (INVARIABILE)
        Persona transmaschile, 60 anni, corpo femminile (seno coppa D, clessidra, 180cm, 85kg).
        ASSOLUTAMENTE SENZA PELI (NO hair on chest/arms/legs).
        VISO: Maschile italiano 60enne, barba grigia curata 5cm, occhiali Vogue ottagonali Havana Dark.
        Capelli: Platino corti ondulati.
        IDENTITY: Il volto deve corrispondere al file master_face.png fornito.

        Regola OUTFIT & AMBIENTAZIONE
        Analisi: {safe_outfit}
        
        ISTRUZIONE CRUCIALE "ANTI-FACESWAP":
        Non fare copia-incolla del volto sull'immagine originale.
        RIGENERA L'INTERA IMMAGINE DA ZERO (PIXEL NUOVI).
        Il soggetto (Valeria) deve essere immerso nell'ambiente descritto.
        La luce sul volto deve matchare perfettamente la luce dell'ambiente.
        Se l'ambiente è "Studio/Plain", inventa un contesto luxury.
        Se l'ambiente è specifico (neve, mare), ricrealo fedelmente attorno a Valeria.

        Impostazioni tecniche
        8K, 85mm, f/2.8.
        FORMATO: {ar_scelto}

        Prompt negativo:
        faceswap, pasted face, photoshop collage, neck seams, bad lighting, female face, body hair, chest hair, young, low quality.
        """

        response = client.models.generate_content(
            model=GEN_MODEL,
            contents=[system_prompt, face_part, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")],
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                safety_settings=[
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            )
        )

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data: return part.inline_data.data, None
        
        finish_reason = getattr(response.candidates[0], 'finish_reason', 'UNKNOWN')
        return None, f"Stop Reason: {finish_reason}"

    except Exception as e: return None, str(e)

# --- HANDLERS ---
@bot.message_handler(func=lambda m: m.reply_to_message is not None and m.text is not None)
def handle_reply_edit(m):
    uid = m.from_user.id
    target_msg = m.reply_to_message
    file_id = None
    if target_msg.document: file_id = target_msg.document.file_id
    elif target_msg.photo: file_id = target_msg.photo[-1].file_id
    
    if file_id:
        bot.reply_to(m, "🔄 Edit Flash V2.30...")
        file_info = bot.get_file(file_id)
        current_img_bytes = bot.download_file(file_info.file_path)
        vision_context = original_outfit_analysis.get(uid, "Fashion ensemble.")
        
        def run_edit():
            res, err = generate_closet_task(current_img_bytes, user_ar[uid], m.text, vision_context, edit_mode=True)
            if res: bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name="v_edit.jpg")
            else: bot.send_message(m.chat.id, f"❌ {err}")
        executor.submit(run_edit)

@bot.message_handler(content_types=['photo'])
def handle_new_photo(m):
    uid = m.from_user.id
    qty, fmt = user_qty[uid], user_ar[uid]
    file_info = bot.get_file(m.photo[-1].file_id)
    img_bytes = bot.download_file(file_info.file_path)
    
    bot.reply_to(m, f"⚡ Flash V2.30 ({qty} scatti)...")
    
    vision_desc = analyze_outfit_vision(img_bytes)
    original_outfit_analysis[uid] = vision_desc
    bot.send_message(m.chat.id, f"📝 <b>Vision Flash:</b> <i>{vogue_sanitize(vision_desc)}</i>")
    
    for i in range(qty):
        def run(idx):
            res, err = generate_closet_task(img_bytes, fmt, m.caption or "", vision_desc)
            if res: bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"v_{idx+1:02d}.jpg")
            else: bot.send_message(m.chat.id, f"❌ Scatto {idx+1}: {err}")
        executor.submit(run, i)

app = flask.Flask(__name__)
@app.route('/')
def h(): return "Bot Online - V2.30 (Flash)"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
