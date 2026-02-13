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

# Usiamo Pro per l'analisi (più intelligente) e Nano per la generazione (più veloce/creativo)
VISION_MODEL = "gemini-1.5-pro" 
GEN_MODEL = "nano-banana-pro-preview"

executor = ThreadPoolExecutor(max_workers=2)

# --- THE VOGUE SHIELD (Sanitizzazione testuale) ---
def vogue_sanitize(text):
    if not text: return ""
    euphemisms = {
        r"\b(bra|reggiseno|sutiã)\b": "luxury bralette",
        r"\b(underwear|panties|calcinha)\b": "silk intimate set",
        r"\b(thong|perizoma|fio dental)\b": "minimalist couture bottom",
        r"\b(nude|nudo|nu)\b": "natural skin texture",
        r"\b(cleavage|decote)\b": "glamorous decolletage",
        r"\b(breast|seno|seios)\b": "feminine torso silhouette",
        r"\b(sexy|hot|quente)\b": "alluring and sophisticated",
        r"\b(see-through|trasparente)\b": "sheer translucent fabric",
    }
    sanitized = text.lower()
    for pattern, replacement in euphemisms.items():
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized.capitalize()

# --- STEP 1: L'ANALIZZATORE VISIVO ---
def analyze_outfit_vision(img_bytes):
    """Analizza l'immagine e restituisce una descrizione tecnica Safe."""
    try:
        prompt = """
        You are a high-fashion technical stylist for Vogue. 
        Analyze the clothing in the image. Describe ONLY the garment: materials, exact cut, 
        texture, patterns, and colors. 
        IGNORE the model's body, face, and pose. 
        Provide a professional description (max 60 words) using technical fashion terms.
        Ensure the description is 'Safe for Work' and editorial in tone.
        """
        
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[
                prompt,
                genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            ]
        )
        return response.text if response.text else ""
    except Exception as e:
        logger.error(f"❌ Errore Vision: {e}")
        return ""

# --- CARICAMENTO IDENTITÀ ---
def get_face_part():
    file_path = "master_face.png"
    if not os.path.exists(file_path): return None
    try:
        with open(file_path, "rb") as f:
            return genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
    except: return None

MASTER_PART = get_face_part()

# --- STEP 2: GENERAZIONE FINALE ---
def generate_closet_task(img_outfit_bytes, ar_scelto, user_notes="", vision_description=""):
    try:
        if not MASTER_PART: return None, "Identità mancante."

        # Combiniamo l'analisi visiva con le note dell'utente e passiamo tutto nello scudo
        full_context = f"{vision_description} {user_notes}"
        safe_context = vogue_sanitize(full_context)

        system_instructions = f"""
        ROLE: Expert Vogue photographer. Fictional fashion catalog.
        SUBJECT: Valeria Cross (60yo, male face, beard, glasses, female D-cup body, hairless).
        OUTFIT DESCRIPTION: {safe_context}
        TECHNICAL: 8K, 85mm, f/2.8. Professional studio lighting.
        """

        contents = [
            f"{system_instructions}\n\nFORMATO: {ar_scelto}\n\nNEGATIVE: female face, young, body hair, peli.",
            MASTER_PART,
            # Passiamo l'immagine originale come riferimento visivo
            genai_types.Part.from_bytes(data=img_outfit_bytes, mime_type="image/jpeg")
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

# --- INTERFACCIA ---
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
user_ar = defaultdict(lambda: "2:3")

@bot.message_handler(content_types=['photo'])
def handle_outfit(m):
    uid = m.from_user.id
    fmt = user_ar[uid]
    caption = m.caption if m.caption else ""
    
    bot.reply_to(m, "🔍 Analisi stilistica in corso...")
    
    file_info = bot.get_file(m.photo[-1].file_id)
    img_bytes = bot.download_file(file_info.file_path)

    # 1. Analisi (Step "Lavaggio")
    vision_desc = analyze_outfit_vision(img_bytes)
    
    bot.reply_to(m, f"👗 <b>Scheda tecnica generata:</b>\n<i>{vision_desc[:150]}...</i>\n\n🚀 Generazione in corso...")

    # 2. Generazione
    def run_task():
        res, err = generate_closet_task(img_bytes, fmt, caption, vision_desc)
        if res:
            bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name="valeria_outfit.jpg")
        else:
            bot.send_message(m.chat.id, f"❌ Errore: {err}")

    executor.submit(run_task)

# (Aggiungi qui il resto del codice Flask e polling come prima)
