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
    raise ValueError("🚨 CLOSET_TOKEN o GOOGLE_API_KEY mancanti su Render!")

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# Modelli: Pro per l'analisi (Vede meglio), Nano per la generazione (Più veloce)
VISION_MODEL = "gemini-1.5-pro" 
GEN_MODEL = "nano-banana-pro-preview"

executor = ThreadPoolExecutor(max_workers=2)
user_ar = defaultdict(lambda: "2:3")

# --- THE VOGUE SHIELD (IT / EN / PT) ---
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
        prompt = "Describe ONLY the clothing in this image: materials, cut, texture, and colors. Ignore the person. Use high-fashion technical terms. Max 50 words."
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[prompt, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")]
        )
        return response.text if response.text else "High-fashion garment."
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return "Editorial outfit."

# --- GENERAZIONE ---
def generate_closet_task(img_bytes, ar_scelto, user_notes, vision_desc):
    try:
        # Carica il volto di Walter (Identity)
        if not os.path.exists("master_face.png"): return None, "Face file missing"
        with open("master_face.png", "rb") as f:
            face_part = genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")

        safe_context = vogue_sanitize(f"{vision_desc} {user_notes}")

        system_prompt = f"""
        ROLE: Expert Vogue photographer. Fictional professional editorial.
        SUBJECT: Valeria Cross (60yo male face, grey beard, glasses, female D-cup body, hairless).
        OUTFIT DESCRIPTION: {safe_context}
        TECHNICAL: 8K, 85mm, f/2.8. Professional studio lighting. 
        """

        contents = [
            f"{system_prompt}\n\nFORMATO: {ar_scelto}\n\nNEGATIVE: female face, young, body hair, peli, nsfw.",
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
        return None, f"Blocco: {getattr(response.candidates[0], 'finish_reason', 'Sconosciuto')}"
    except Exception as e: return None, str(e)

# --- BOT LOGIC ---
@bot.message_handler(commands=['start', 'settings'])
def settings(m):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("2:3 🖼️", callback_data="ar_2:3"), types.InlineKeyboardButton("3:2 📷", callback_data="ar_3:2"))
    bot.send_message(m.chat.id, "<b>👗 Valeria Closet Bot Safety+</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    if "ar_" in call.data: user_ar[call.from_user.id] = call.data.replace("ar_", "")
    bot.answer_callback_query(call.id, "OK")

@bot.message_handler(content_types=['photo'])
def handle_outfit(m):
    fmt = user_ar[m.from_user.id]
    caption = m.caption if m.caption else ""
    bot.reply_to(m, "🔍 Analisi stilistica in corso...")
    
    file_info = bot.get_file(m.photo[-1].file_id)
    img_bytes = bot.download_file(file_info.file_path)

    def run():
        vision_desc = analyze_outfit_vision(img_bytes)
        bot.send_message(m.chat.id, f"👗 <b>Analisi:</b> <i>{vogue_sanitize(vision_desc)}</i>")
        res, err = generate_closet_task(img_bytes, fmt, caption, vision_desc)
        if res:
            bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name="valeria_outfit.jpg")
        else:
            bot.send_message(m.chat.id, f"❌ {err}")

    executor.submit(run)

# --- FLASK ---
app = flask.Flask(__name__)
@app.route('/')
def h(): return "Bot Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
    
