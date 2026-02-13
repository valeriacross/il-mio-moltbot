import os, io, threading, logging, flask, telebot, re
from telebot import types
from google import genai
from google.genai import types as genai_types
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE ---
TOKEN = os.environ.get("CLOSET_TOKEN")
API_KEY = os.environ.get("GOOGLE_API_KEY")

if not TOKEN or not API_KEY:
    raise ValueError("🚨 Variabili d'ambiente mancanti su Render!")

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

MODEL_ID = "nano-banana-pro-preview"
executor = ThreadPoolExecutor(max_workers=2)

# --- THE VOGUE SHIELD (IT / EN / PT) ---
def vogue_sanitize(text):
    if not text: return ""
    
    # Mappa trilingue dei termini a rischio
    euphemisms = {
        # Lingerie & Intimo
        r"\b(bra|reggiseno|soutien|sutiã)\b": "luxury bralette",
        r"\b(underwear|mutande|panties|calcinha|cueca)\b": "intimate silk apparel",
        r"\b(thong|perizoma|fio dental)\b": "minimalist couture bottom",
        r"\b(lingerie|intimo|roupa íntima)\b": "boudoir fashion set",
        
        # Anatomia & Pelle
        r"\b(nude|nudo|nu|nua)\b": "natural skin texture",
        r"\b(cleavage|scollatura|decote)\b": "glamorous decolletage",
        r"\b(breast|seno|seios|peito)\b": "feminine torso silhouette",
        r"\b(butt|booty|culo|bumbum|rabo)\b": "lower silhouette",
        
        # Stile & Trasparenze
        r"\b(see-through|trasparente|transparente)\b": "sheer translucent fabric",
        r"\b(sexy|hot|quente|seducente)\b": "alluring and sophisticated",
        r"\b(mini skirt|minigonna|minissaia)\b": "high-fashion mini skirt",
        r"\b(nacked|spogliata|pelada)\b": "bare skin editorial style",
    }
    
    sanitized = text.lower()
    for pattern, replacement in euphemisms.items():
        sanitized = re.sub(pattern, replacement, sanitized)
    
    return sanitized.capitalize()

# --- CARICAMENTO IDENTITÀ ---
def get_face_part():
    file_path = "master_face.png"
    if not os.path.exists(file_path): return None
    try:
        with open(file_path, "rb") as f:
            return genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
    except: return None

MASTER_PART = get_face_part()

# --- GENERAZIONE CORE ---
def generate_closet_task(img_outfit_bytes, ar_scelto, user_instructions=""):
    try:
        if not MASTER_PART: return None, "Identità mancante."

        # Applicazione scudo linguistico
        safe_instructions = vogue_sanitize(user_instructions)
        
        custom_logic = f'‼️ PRIORITÀ: "{safe_instructions}"' if safe_instructions else "Usa ambiente automatico."

        system_instructions = f"""
        OUTFIT 👗: Genera immagine HD usando il canvas caricato. Focus tecnico sui tessuti.
        SOGGETTO: Persona transmaschile 60enne (Valeria Cross). Viso maschile, barba grigia, occhiali Vogue. 
        Corpo femminile clessidra, seno coppa D. DEPILAZIONE TOTALE ASSOLUTA (NO PELI).
        REGOLA OUTFIT: Applica ESCLUSIVAMENTE il capo caricato. {custom_logic}
        TECHNICAL: 8K, 85mm, f/2.8. Finish glossy organico.
        """

        contents = [
            f"{system_instructions}\n\nFORMATO: {ar_scelto}\n\nNEGATIVE: female face, young, body hair, peli.",
            MASTER_PART,
            genai_types.Part.from_bytes(data=img_outfit_bytes, mime_type="image/jpeg")
        ]

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                safety_settings=[{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}]
            )
        )

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data: return part.inline_data.data, None
        return None, f"Blocco: {getattr(response.candidates[0], 'finish_reason', 'Sconosciuto')}"
    except Exception as e: return None, str(e)

# --- INTERFACCIA TELEGRAM ---
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
user_ar = defaultdict(lambda: "2:3")
user_qty = defaultdict(lambda: 2)

@bot.message_handler(commands=['start', 'settings'])
def settings(m):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("2:3 🖼️", callback_data="ar_2:3"), types.InlineKeyboardButton("3:2 📷", callback_data="ar_3:2"))
    markup.row(types.InlineKeyboardButton("16:9 🎬", callback_data="ar_16:9"), types.InlineKeyboardButton("9:16 📲", callback_data="ar_9:16"))
    markup.row(types.InlineKeyboardButton("1 Foto", callback_data="qty_1"), types.InlineKeyboardButton("2 Foto", callback_data="qty_2"))
    bot.send_message(m.chat.id, "<b>👗 Valeria Closet Bot (Trilingue)</b>\nIT 🇮🇹 | EN 🇬🇧 | PT 🇵🇹\nInvia l'outfit e scrivi le tue note.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    uid = call.from_user.id
    if "ar_" in call.data: user_ar[uid] = call.data.replace("ar_", "")
    if "qty_" in call.data: user_qty[uid] = int(call.data.replace("qty_", ""))
    bot.answer_callback_query(call.id, "Configurazione salvata")

@bot.message_handler(content_types=['photo'])
def handle_outfit(m):
    uid = m.from_user.id
    qty, fmt = user_qty[uid], user_ar[uid]
    caption = m.caption if m.caption else ""
    bot.reply_to(m, f"👗 Analisi trilingue e prova abito in corso...")
    
    file_info = bot.get_file(m.photo[-1].file_id)
    img_bytes = bot.download_file(file_info.file_path)

    def run_task(i):
        res, err = generate_closet_task(img_bytes, fmt, caption)
        if res:
            bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"closet_{i+1}.jpg")
        else:
            bot.send_message(m.chat.id, f"❌ Errore {i+1}: {err}")

    for i in range(qty):
        executor.submit(run_task, i)

app = flask.Flask(__name__)
@app.route('/')
def h(): return "Closet Bot Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
    
