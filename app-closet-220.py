# ---------------------------------------------------------
# VERSION: V2.20 (Golden Copy - Restored)
# TIMESTAMP: 2026-02-13 23:35 WET
# STATUS: Waiting for API Quota Reset (Error 429)
# LOGIC: 
# - Model: gemini-3-pro-image-preview (High Fidelity Img2Img)
# - Prompt: Pose Unlocked ("Use as visual reference", "Pose MUST be new")
# - Features: Menus (6 AR, 1-2-4 Qty), Edit via Reply.
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

# --- MODELLI (La combinazione vincente della V2.20) ---
VISION_MODEL = "models/gemini-3-flash-preview"
GEN_MODEL = "models/gemini-3-pro-image-preview"

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
    bot.send_message(m.chat.id, "<b>👗 Valeria Closet Settings (V2.20 Restored)</b>\nScegli il formato e il numero di scatti:", 
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
        prompt = "Describe the clothing: materials, cut, colors, textures. Technical fashion terms. Max 50 words."
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
            MODIFICA QUESTA IMMAGINE SPECIFICA: {safe_notes}.
            MANTIENI TUTTO L'ENSEMBLE: Non cambiare il volto, la pettinatura, l'abito o lo sfondo presenti nell'immagine caricata. 
            Intervieni solo per applicare la modifica richiesta mantenendo la massima coerenza visiva.
            """
        else:
            # LOGICA V2.20: Posa Sbloccata ("Reference Visivo" invece di "Canvas")
            mode_instruction = "Genera un'immagine in alta risoluzione utilizzando l’immagine caricata come riferimento visivo per l'abito e i suoi dettagli."

        system_prompt = f"""
        OUTFIT 👗
        {mode_instruction}
        Foto per catalogo di alta moda, illuminazione da studio professionale, posa statuaria ed elegante, nessuna allusione, focus tecnico sui tessuti.

        IL SOGGETTO
        Ritratto editoriale ultra-realista e dinamico di una persona transmaschile di 60 anni, alta 180cm e 85kg. Il soggetto presenta le distinte caratteristiche facciali di un uomo italiano vissuto: occhi castani/verde scuro, occhiali Vogue con montatura ottagonale colore Havana dark, una barba grigia curata e naturale di circa 5 cm, e capelli grigi platino ondulati, corti ai lati e più lunghi sopra (massimo 15 cm), leggermente spettinati con un tocco di movimento. Il viso ha una struttura ovale-rettangolare, incorniciato da un'espressione calma e saggia, con un mezzo sorriso autentico che increspa gli angoli della bocca. Si notano rughe espressive e borse sotto gli occhi, labbra sottili e naturali. La pelle del viso è ultra-dettagliata, con pori visibili e micro-texture.
        La persona ha un seno prosperoso coppa D. Caratteristica imprescindibile è l'assenza totale, rigorosa e assoluta di peli su tutto il corpo. La pelle deve apparire perfettamente liscia e priva di peluria. Corpo a clessidra.
        Il volto è armoniosamente fuso con il corpo, in perfetta coerenza con la luce e la prospettiva della scena.
        IDENTITY PRIORITY: Usa l'immagine master_face.png fornita come riferimento assoluto per il volto.

        Regola OUTFIT
        L’abbigliamento e i dettagli visivi vengono presi dall'immagine analizzata: {safe_outfit}.
        L’outfit deve essere riprodotto con massima fedeltà: materiali, taglio, tessuti, colori e texture identici all’immagine di riferimento.
        Non modificare il design o i materiali dell'outfit. La posa DEVE essere nuova, dinamica ed editoriale, NON statica come nell'immagine di riferimento.
        Ambientazione automatica (se non specificato diversamente): Lingerie->Camera, Bikini->Spiaggia/Piscina, Abito->Galà, Casual->Urbana.

        Impostazioni fotografiche
        Risoluzione 8K, obiettivo 85mm, f/2.8, ISO 200, shutter 1/160, bokeh naturale, finish glossy iper-dettagliato.
        FORMATO RICHIESTO: {ar_scelto}

        Prompt negativo fisso:
        female face, woman, girl, young, unrealistic skin, long feminine hair, body hair, chest hair, breast hair, peli sul seno, static pose, mannequin pose.
        """

        response = client.models.generate_content(model=GEN_MODEL,
            contents=[system_prompt, face_part, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")],
            config=genai_types.GenerateContentConfig(response_modalities=["IMAGE"],
            safety_settings=[{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}]))

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data: return part.inline_data.data, None
        return None, "Errore Rendering o Blocco Safety"
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
        bot.reply_to(m, "🔄 Elaborazione modifica sull'immagine corrente...")
        file_info = bot.get_file(file_id)
        current_img_bytes = bot.download_file(file_info.file_path)
        vision_context = original_outfit_analysis.get(uid, "High-fashion ensemble.")
        
        def run_edit():
            res, err = generate_closet_task(current_img_bytes, user_ar[uid], m.text, vision_context, edit_mode=True)
            if res: bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name="valeria_refined.jpg")
            else: bot.send_message(m.chat.id, f"❌ {err}")
        executor.submit(run_edit)

@bot.message_handler(content_types=['photo'])
def handle_new_photo(m):
    uid = m.from_user.id
    qty, fmt = user_qty[uid], user_ar[uid]
    file_info = bot.get_file(m.photo[-1].file_id)
    img_bytes = bot.download_file(file_info.file_path)
    
    bot.reply_to(m, f"🔍 Analisi Vogue e produzione di {qty} scatti (Formato {fmt}) in corso...")
    
    vision_desc = analyze_outfit_vision(img_bytes)
    original_outfit_analysis[uid] = vision_desc
    bot.send_message(m.chat.id, f"📝 <b>Analisi Vogue:</b> <i>{vogue_sanitize(vision_desc)}</i>")
    
    for i in range(qty):
        def run(idx):
            res, err = generate_closet_task(img_bytes, fmt, m.caption or "", vision_desc)
            if res: bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"valeria_{idx+1}.jpg")
            else: bot.send_message(m.chat.id, f"❌ Scatto {idx+1}: {err}")
        executor.submit(run, i)

app = flask.Flask(__name__)
@app.route('/')
def h(): return "Bot Online - V2.20 Restored"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
    
