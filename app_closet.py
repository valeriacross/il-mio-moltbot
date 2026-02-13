import os, io, threading, logging, flask, telebot
from telebot import types
from google import genai
from google.genai import types as genai_types
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE BLINDATA ---
TOKEN = os.environ.get("CLOSET_TOKEN")
API_KEY = os.environ.get("GOOGLE_API_KEY")

if not TOKEN: raise ValueError("🚨 CLOSET_TOKEN mancante su Render!")
if not API_KEY: raise ValueError("🚨 GOOGLE_API_KEY mancante su Render!")

client = genai.Client(api_key=API_KEY)
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

MODEL_ID = "nano-banana-pro-preview"

user_ar = defaultdict(lambda: "2:3")    # Default Verticale
user_qty = defaultdict(lambda: 2)         # Default 2 scatti

executor = ThreadPoolExecutor(max_workers=2)

# --- CARICAMENTO MASTER FACE ---
def get_face_part():
    file_path = "master_face.png"
    if not os.path.exists(file_path):
        logger.error(f"🚨 ERRORE: {file_path} non trovato!")
        return None
    try:
        with open(file_path, "rb") as f:
            return genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
    except Exception as e:
        logger.error(f"❌ Errore lettura file: {e}")
        return None

MASTER_PART = get_face_part()

# --- LOGICA CLOSET (CON DIDASCALIA) ---
# Ora accetta anche user_instructions (la didascalia)
def generate_closet_task(img_outfit_bytes, ar_scelto, user_instructions=""):
    try:
        if not MASTER_PART: return None, "Errore interno: Identità mancante."

        # Logica condizionale per le istruzioni
        ambiente_rules = """
        REGOLE AMBIENTE AUTOMATICO (Default):
        Lingerie/Pigiama->Camera da letto; Bikini->Spiaggia/Piscina; 
        Elegante->Gala/Sera; Casual->Urbano; Sportivo->Palestra.
        """
        
        custom_instructions = ""
        if user_instructions:
            # Se c'è una didascalia, diamo priorità a quella
            custom_instructions = f"""
            ‼️ ISTRUZIONI UTENTE PRIORITARIE: L'utente ha specificato: "{user_instructions}".
            ESEGUI queste istruzioni per la posa e l'ambientazione, IGNORANDO le regole automatiche di ambiente se in conflitto.
            Mantieni SEMPRE l'outfit caricato.
            """
        else:
            # Altrimenti usa le regole automatiche
            custom_instructions = ambiente_rules

        system_instructions = f"""
        OUTFIT 👗: Genera un'immagine in alta risoluzione utilizzando come canvas l’immagine caricata.
        Foto per catalogo di alta moda, focus tecnico sui tessuti.
        
        IL SOGGETTO: Persona transmaschile italiana di 60 anni (Walter/Valeria). 
        Viso maschile con barba grigia, occhiali Vogue. Corpo femminile clessidra, seno coppa D. 
        DEPILAZIONE TOTALE E ASSOLUTA su tutto il corpo. Pelle iper-dettagliata.
        
        REGOLA OUTFIT INDEROGABILE: Estrai ed applica ESCLUSIVAMENTE il capo e i dettagli (taglio, materiali, pattern) 
        dall'immagine caricata. Ignora il modello originale.
        
        {custom_instructions}
        
        TECHNICAL: 8K, 85mm, f/2.8. Focus su volto e torso. Finish glossy organico.
        """

        negatives = "NEGATIVE: female face, young, body hair, chest hair, peli, long hair, plastic skin, distorted outfit."

        contents = [
            f"{system_instructions}\n\nFORMATO: {ar_scelto}\n\n{negatives}",
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

        if not response or not response.candidates: return None, "Server Google non risponde."
        candidate = response.candidates[0]
        
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if part.inline_data: return part.inline_data.data, None
        
        reason = getattr(candidate, 'finish_reason', 'Sconosciuto')
        return None, f"🛡️ Blocco Sicurezza: {reason}"

    except Exception as e:
        logger.error(f"❌ Errore: {e}")
        return None, str(e)

# --- BOT INTERFACE ---
@bot.message_handler(commands=['start', 'settings'])
def settings(m):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("2:3 🖼️ (Default)", callback_data="ar_2:3"),
               types.InlineKeyboardButton("3:2 📷", callback_data="ar_3:2"))
    markup.row(types.InlineKeyboardButton("16:9 🎬", callback_data="ar_16:9"),
               types.InlineKeyboardButton("9:16 📲", callback_data="ar_9:16"))
    markup.row(types.InlineKeyboardButton("1 Foto", callback_data="qty_1"),
               types.InlineKeyboardButton("2 Foto (Default)", callback_data="qty_2"))
    bot.send_message(m.chat.id, "<b>👗 Valeria Closet Bot</b>\nCarica la foto di un outfit. Aggiungi una didascalia per specificare posa o ambiente!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    uid = call.from_user.id
    if "ar_" in call.data: user_ar[uid] = call.data.replace("ar_", "")
    if "qty_" in call.data: user_qty[uid] = int(call.data.replace("qty_", ""))
    bot.answer_callback_query(call.id, "Impostazioni aggiornate")

@bot.message_handler(content_types=['photo'])
def handle_outfit(m):
    uid = m.from_user.id
    qty = user_qty[uid]
    fmt = user_ar[uid]
    # Estrae la didascalia (se presente)
    caption = m.caption if m.caption else ""
    
    msg_text = f"👗 Provo l'outfit...\n(Batch: {qty} - {fmt})"
    if caption: msg_text += f"\n📝 Note: <i>{caption}</i>"
    bot.reply_to(m, msg_text)
    
    file_info = bot.get_file(m.photo[-1].file_id)
    img_bytes = bot.download_file(file_info.file_path)

    def task(i):
        # Passa anche la caption alla funzione di generazione
        res, err = generate_closet_task(img_bytes, fmt, caption)
        if res:
            bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"closet_{i+1}.jpg")
        else:
            bot.send_message(m.chat.id, f"❌ Errore scatto {i+1}: {err}")

    for i in range(qty):
        executor.submit(task, i)

@bot.message_handler(content_types=['text'])
def no_text(m):
    bot.reply_to(m, "Usa una <b>FOTO</b> con didascalia per il Virtual Try-On! 👗")

# --- RUN ---
app = flask.Flask(__name__)
@app.route('/')
def h(): return "Closet Bot V2 (Caption Aware) Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling()
        
