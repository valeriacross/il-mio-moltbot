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

# --- MODELLI DALLA TUA LISTA ---
VISION_MODEL = "gemini-3-flash-preview"       # FUNZIONA: Estrae la scheda tecnica
GEN_MODEL = "gemini-3-pro-image-preview"      # NUOVO: Genera l'immagine multimodale

executor = ThreadPoolExecutor(max_workers=4)
user_ar = defaultdict(lambda: "2:3")

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

# --- STEP 1: ANALISI ---
def analyze_outfit_vision(img_bytes):
    try:
        prompt = "Describe the clothing in detail: colors, fabric, patterns, and cut. Technical fashion terms only. Max 50 words."
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[prompt, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")]
        )
        return response.text if response.text else "High-fashion garment."
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return "Editorial fashion set."

# --- STEP 2: GENERAZIONE ---
def generate_closet_task(img_bytes, ar_scelto, user_notes, vision_desc):
    try:
        if not os.path.exists("master_face.png"): return None, "Identity file missing"
        with open("master_face.png", "rb") as f:
            face_part = genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")

        safe_context = vogue_sanitize(f"{vision_desc} {user_notes}")

        # Prompt per modello multimodale
        system_prompt = f"""
        TASK: Generate a high-fashion editorial photo.
        SUBJECT: Valeria Cross, 60yo persona, Italian male face, grey beard, Vogue glasses, female D-cup body, hairless skin.
        OUTFIT TO APPLY: {safe_context}. Use the provided outfit image as a technical reference.
        STYLE: Professional studio, 85mm f/2.8, magazine quality.
        FORMAT: {ar_scelto}
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
    bot.send_message(m.chat.id, "<b>👗 Valeria Closet Bot V2.7 (Gemini 3 Pro)</b>\nAnalisi attiva e 2 scatti paralleli.")

@bot.message_handler(content_types=['photo'])
def handle_outfit(m):
    fmt = user_ar[m.from_user.id]
    caption = m.caption if m.caption else ""
    bot.reply_to(m, "🔍 Analisi Gemini 3 e creazione multimodale...")
    
    file_info = bot.get_file(m.photo[-1].file_id)
    img_bytes = bot.download_file(file_info.file_path)

    # Analisi (Step "Lavaggio")
    vision_desc = analyze_outfit_vision(img_bytes)
    bot.send_message(m.chat.id, f"📝 <b>Scheda Vogue:</b> <i>{vogue_sanitize(vision_desc)}</i>")

    # 2 scatti paralleli
    for i in range(2):
        def run_gen(idx):
            res, err = generate_closet_task(img_bytes, fmt, caption, vision_desc)
            if res:
                bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"valeria_v27_{idx+1}.jpg")
            else:
                bot.send_message(m.chat.id, f"❌ Scatto {idx+1}: {err}")
        
        executor.submit(run_gen, i)

# --- FLASK ---
app = flask.Flask(__name__)
@app.route('/')
def h(): return "Bot Online - V2.7"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
    
