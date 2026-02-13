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

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

VISION_MODEL = "gemini-1.5-pro" 
GEN_MODEL = "nano-banana-pro-preview"

executor = ThreadPoolExecutor(max_workers=4) # Aumentato per gestire 2 scatti paralleli
user_ar = defaultdict(lambda: "2:3")
user_qty = defaultdict(lambda: 2) # Ripristinato Default a 2

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
        r"\b(mini skirt|minigonna|minissaia)\b": "high-fashion mini skirt",
        r"\b(bikini|costume)\b": "high-fashion swimwear set",
    }
    sanitized = text.lower()
    for pattern, replacement in euphemisms.items():
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized.capitalize()

# --- ANALIZZATORE VISIVO ---
def analyze_outfit_vision(img_bytes):
    try:
        prompt = "Describe ONLY the clothing: materials, cut, and colors. Ignore the person. Use high-fashion technical terms. Max 40 words."
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[prompt, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")]
        )
        return response.text if response.text else "Editorial garment."
    except: return "High-fashion outfit."

# --- GENERAZIONE ---
def generate_closet_task(img_bytes, ar_scelto, user_notes, vision_desc):
    try:
        if not os.path.exists("master_face.png"): return None, "Face missing"
        with open("master_face.png", "rb") as f:
            face_part = genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")

        safe_context = vogue_sanitize(f"{vision_desc} {user_notes}")

        system_prompt = f"""
        ROLE: Expert Vogue photographer. Fictional professional editorial.
        SUBJECT: Valeria Cross (60yo male face, grey beard, glasses, female D-cup body, hairless).
        OUTFIT: {safe_context}
        STYLE: High-end fashion catalog, tasteful, professional.
        TECHNICAL: 85mm, f/2.8. Professional studio lighting.
        """

        contents = [
            f"{system_prompt}\n\nFORMATO: {ar_scelto}\n\nNEGATIVE: female face, young, body hair, peli, nsfw, explicit.",
            face_part,
            genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
        ]

        response = client.models.generate_content(
            model=GEN_MODEL,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                safety_settings=[{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}]
            )
        )

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data: return part.inline_data.data, None
        
        reason = getattr(response.candidates[0], 'finish_reason', 'Sconosciuto')
        return None, f"Blocco: {reason}"
    except Exception as e: return None, str(e)

# --- BOT LOGIC ---
@bot.message_handler(commands=['start', 'settings'])
def settings(m):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("2:3 🖼️", callback_data="ar_2:3"), types.InlineKeyboardButton("3:2 📷", callback_data="ar_3:2"))
    markup.row(types.InlineKeyboardButton("1 Foto", callback_data="qty_1"), types.InlineKeyboardButton("2 Foto", callback_data="qty_2"))
    bot.send_message(m.chat.id, "<b>👗 Valeria Closet Bot V2.3</b>\nScegli formato e quantità.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    uid = call.from_user.id
    if "ar_" in call.data: user_ar[uid] = call.data.replace("ar_", "")
    if "qty_" in call.data: user_qty[uid] = int(call.data.replace("qty_", ""))
    bot.answer_callback_query(call.id, "Impostazioni salvate")

@bot.message_handler(content_types=['photo'])
def handle_outfit(m):
    uid = m.from_user.id
    qty, fmt = user_qty[uid], user_ar[uid]
    caption = m.caption if m.caption else ""
    bot.reply_to(m, "🔍 Analisi stilistica e preparazione scatti...")
    
    file_info = bot.get_file(m.photo[-1].file_id)
    img_bytes = bot.download_file(file_info.file_path)

    # Analisi fatta una volta sola per risparmiare tempo
    vision_desc = analyze_outfit_vision(img_bytes)
    bot.send_message(m.chat.id, f"📝 <b>Scheda Vogue:</b> <i>{vogue_sanitize(vision_desc)}</i>")

    def run_gen(i):
        res, err = generate_closet_task(img_bytes, fmt, caption, vision_desc)
        if res:
            bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"closet_{i+1}.jpg")
        else:
            bot.send_message(m.chat.id, f"❌ Scatto {i+1}: {err}")

    for i in range(qty):
        executor.submit(run_gen, i)

# --- FLASK ---
app = flask.Flask(__name__)
@app.route('/')
def h(): return "Bot Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
    
