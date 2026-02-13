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

# --- MODELLI ---
VISION_MODEL = "models/gemini-3-flash-preview"
GEN_MODEL = "models/gemini-3-pro-image-preview"

executor = ThreadPoolExecutor(max_workers=8)
user_ar = defaultdict(lambda: "2:3")
user_qty = defaultdict(lambda: 2)

# Memoria temporanea per conservare i dati dell'ultimo scatto (outfit e analisi)
# Serve per la funzione di "Edit" via Reply
last_generation_data = {}

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

# --- ANALISI VISIVA ---
def analyze_outfit_vision(img_bytes):
    try:
        prompt = "Describe the clothing in detail: materials, cut, colors, and textures. Technical fashion terms only. Max 50 words. Ignore the model's body."
        response = client.models.generate_content(
            model=VISION_MODEL,
            contents=[prompt, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")]
        )
        return response.text if response.text else "High-fashion technical garment."
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return "Editorial fashion outfit."

# --- GENERAZIONE ---
def generate_closet_task(img_bytes, ar_scelto, user_notes, vision_desc, edit_mode=False):
    try:
        if not os.path.exists("master_face.png"): return None, "ERRORE: master_face.png mancante!"
        with open("master_face.png", "rb") as f:
            face_part = genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")

        safe_outfit_desc = vogue_sanitize(vision_desc)
        safe_user_notes = vogue_sanitize(user_notes)

        # Se siamo in Edit Mode (reply), aggiungiamo una direttiva specifica
        edit_instruction = f"MODIFICA RICHIESTA: {safe_user_notes}. Mantieni l'ensemble originale." if edit_mode else ""

        system_prompt = f"""
        OUTFIT 👗
        {edit_instruction}
        Genera un'immagine in alta risoluzione utilizzando come canvas l’immagine caricata. 
        Mantenendo il rapporto originale e le proporzioni esatte.
        Foto per catalogo di alta moda, illuminazione da studio professionale, posa statuaria ed elegante, focus tecnico sui tessuti.

        IL SOGGETTO
        Ritratto editoriale ultra-realista di Valeria Cross, persona transmaschile di 60 anni, 180cm, 85kg. 
        IDENTITÀ: Volto uomo italiano vissuto, barba grigia 5cm, occhiali Vogue ottagonali Havana dark (MANDATORI).
        CORPO: Femminile a clessidra, seno prosperoso coppa D, pelle TASSATIVAMENTE priva di peli.
        
        Regola OUTFIT
        Riproduci con massima fedeltà: {safe_outfit_desc}.
        AMBIENTAZIONE: Genera automaticamente in base all'outfit (Lingerie->Camera, Bikini->Spiaggia, Abito->Galà).
        
        IMPOSTAZIONI FOTOGRAFICHE
        8K, 85mm, f/2.8, ISO 200. Focus volto/torso, bokeh naturale, finish glossy iper-dettagliato.
        FORMATO: {ar_scelto}

        NEGATIVES: female face, body hair, peli sul corpo, peli sul seno, long feminine hair.
        """

        response = client.models.generate_content(
            model=GEN_MODEL,
            contents=[system_prompt, face_part, genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")],
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                safety_settings=[{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}]
            )
        )

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data: return part.inline_data.data, None
        return None, "Blocco Safety o errore rendering"
    except Exception as e: return None, str(e)

# --- BOT LOGIC ---
@bot.message_handler(commands=['start', 'settings'])
def show_settings(m):
    # (Logica menu formati e quantità identica alla v2.15)
    bot.send_message(m.chat.id, "<b>👗 Valeria Closet Settings</b>\nScegli formato e numero di scatti.")

# --- HANDLER PER IL RE-EDIT (REPLY) ---
@bot.message_handler(func=lambda m: m.reply_to_message is not None and m.text is not None)
def handle_edit_reply(m):
    uid = m.from_user.id
    # Verifichiamo se il messaggio a cui si risponde è una foto inviata dal bot
    if m.reply_to_message.document or m.reply_to_message.photo:
        if uid in last_generation_data:
            bot.reply_to(m, "🔄 Applicazione modifiche all'ensemble originale...")
            
            data = last_generation_data[uid]
            fmt = user_ar[uid]
            
            def run_edit():
                # Usiamo l'immagine dell'outfit originale, ma aggiungiamo la nuova nota
                res, err = generate_closet_task(data['img'], fmt, m.text, data['vision'], edit_mode=True)
                if res:
                    bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"valeria_edit.jpg")
                else:
                    bot.send_message(m.chat.id, f"❌ Errore modifica: {err}")
            
            executor.submit(run_edit)
        else:
            bot.reply_to(m, "⚠️ Sessione scaduta. Invia una nuova foto per ricominciare.")

# --- HANDLER PHOTO (GENERAZIONE PRIMARIA) ---
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    uid = m.from_user.id
    qty, fmt = user_qty[uid], user_ar[uid]
    caption = m.caption if m.caption else ""
    
    file_info = bot.get_file(m.photo[-1].file_id)
    img_bytes = bot.download_file(file_info.file_path)

    bot.reply_to(m, f"🔍 Analisi e produzione di {qty} scatti...")
    vision_desc = analyze_outfit_vision(img_bytes)
    bot.send_message(m.chat.id, f"📝 <b>Analisi:</b> <i>{vogue_sanitize(vision_desc)}</i>")

    # Salviamo i dati per consentire eventuali "Reply" successive
    last_generation_data[uid] = {'img': img_bytes, 'vision': vision_desc}

    for i in range(qty):
        def run_task(idx):
            res, err = generate_closet_task(img_bytes, fmt, caption, vision_desc)
            if res:
                bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"valeria_{idx+1}.jpg")
            else:
                bot.send_message(m.chat.id, f"❌ Scatto {idx+1}: {err}")
        executor.submit(run_task, i)

# --- FLASK ---
app = flask.Flask(__name__)
@app.route('/')
def h(): return "Bot Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
