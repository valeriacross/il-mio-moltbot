import os, io, threading, logging, flask, telebot
from telebot import types
from google import genai
from google.genai import types as genai_types
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE ---
# Usa un NUOVO Token Telegram qui!
TOKEN = os.environ.get("CLOSET_TOKEN") 
API_KEY = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=API_KEY)

MODEL_ID = "nano-banana-pro-preview"

user_ar = defaultdict(lambda: "2:3")    # Default per Closet: Verticale
user_qty = defaultdict(lambda: 2)         # Default 2 scatti per confronto

executor = ThreadPoolExecutor(max_workers=2)

# --- MASTER FACE ---
def get_face_part():
    try:
        with open("master_face.png", "rb") as f:
            return genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
    except Exception as e:
        logger.error(f"❌ Master Face mancante: {e}")
        return None

MASTER_PART = get_face_part()

# --- LOGICA CLOSET (VIRTUAL TRY-ON) ---
def generate_closet_task(img_outfit_bytes, ar_scelto):
    try:
        if not MASTER_PART: return None, "Manca master_face.png"

        # Il tuo Master Prompt OUTFIT integrato
        system_instructions = """
        OUTFIT 👗: Genera un'immagine in alta risoluzione utilizzando come canvas l’immagine caricata, 
        mantenendo il suo rapporto originale e le proporzioni esatte. 
        Foto per catalogo di alta moda, focus tecnico sui tessuti.
        
        IL SOGGETTO: Persona transmaschile italiana di 60 anni, 180cm, 85kg. 
        Occhi castani/verdi, occhiali Vogue ottagonali Havana dark. Barba grigia 5cm. 
        Capelli grigio platino ondulati, corti ai lati, sopra max 15cm.
        Corpo: Seno coppa D, depilazione totale, assoluta e rigorosa su tutto il corpo. 
        Pelle iper-dettagliata con pori e rughe naturali. Proporzioni a clessidra.
        
        REGOLA OUTFIT: Estrai esclusivamente il capo e i dettagli (taglio, materiali, colori) 
        dall'immagine caricata. Ignora il volto e il corpo del modello originale.
        Genera l'ambiente coerente: Lingerie->Camera; Bikini->Spiaggia/Piscina; 
        Elegante->Gala; Casual->Urbano; Sportivo->Palestra.
        
        TECHNICAL: 8K, 85mm, f/2.8, ISO 200. Focus su volto e torso. 
        Bokeh cremoso, finish glossy organico.
        """

        negatives = "NEGATIVE: female face, woman, young, body hair, chest hair, peli sul seno, long hair, plastic skin."

        # Ordine dei contenuti per il modello
        contents = [
            f"{system_instructions}\n\nFORMATO RICHIESTO: {ar_scelto}\n\n{negatives}",
            MASTER_PART, # Chi è Valeria
            genai_types.Part.from_bytes(data=img_outfit_bytes, mime_type="image/jpeg") # Cosa deve indossare
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
                if part.inline_data:
                    return part.inline_data.data, None
        
        # Diagnostica rapida
        if response.candidates and response.candidates[0].finish_reason != "STOP":
            return None, f"Blocco sicurezza: {response.candidates[0].finish_reason}"
            
        return None, "Errore generico."
    except Exception as e:
        return None, str(e)

# --- BOT INTERFACE ---
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

@bot.message_handler(commands=['start', 'settings'])
def settings(m):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("3:2 📷", callback_data="ar_3:2"),
               types.InlineKeyboardButton("2:3 🖼️", callback_data="ar_2:3"))
    markup.row(types.InlineKeyboardButton("1 Foto", callback_data="qty_1"),
               types.InlineKeyboardButton("2 Foto", callback_data="qty_2"),
               types.InlineKeyboardButton("4 Foto", callback_data="qty_4"))
    bot.send_message(m.chat.id, "<b>👗 Valeria Closet Bot</b>\nCarica la foto di un outfit per vederlo indossato da Valeria.", reply_markup=markup)

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
    
    bot.reply_to(m, f"👗 Analisi outfit in corso...\nValeria sta provando l'abito (Batch: {qty} - {fmt})")
    
    file_info = bot.get_file(m.photo[-1].file_id)
    img_bytes = bot.download_file(file_info.file_path)

    def task(i):
        res, err = generate_closet_task(img_bytes, fmt)
        if res:
            bot.send_document(m.chat.id, io.BytesIO(res), visible_file_name=f"closet_{i+1}.jpg")
        else:
            bot.send_message(m.chat.id, f"❌ Errore scatto {i+1}: {err}")

    for i in range(qty):
        executor.submit(task, i)

@bot.message_handler(content_types=['text'])
def no_text(m):
    bot.reply_to(m, "Invia una <b>FOTO</b> di un outfit per iniziare il Virtual Try-On! 👗")

# --- RUN ---
app = flask.Flask(__name__)
@app.route('/')
def h(): return "Closet Bot Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.infinity_polling()
