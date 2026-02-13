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

executor = ThreadPoolExecutor(max_workers=8) # Aumentato per gestire fino a 4 scatti paralleli
user_ar = defaultdict(lambda: "2:3")
user_qty = defaultdict(lambda: 2)

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
def generate_closet_task(img_bytes, ar_scelto, user_notes, vision_desc):
    try:
        if not os.path.exists("master_face.png"): 
            return None, "ERRORE: master_face.png non trovato!"
        
        with open("master_face.png", "rb") as f:
            face_part = genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")

        safe_outfit_desc = vogue_sanitize(vision_desc)
        safe_user_notes = vogue_sanitize(user_notes)

        # IL TUO PROMPT ORIGINALE INTEGRALE
        system_prompt = f"""
        OUTFIT 👗
        Genera un'immagine in alta risoluzione utilizzando come canvas l’immagine caricata, mantenendo il suo rapporto originale e le proporzioni esatte.
        Foto per catalogo di alta moda, illuminazione da studio professionale, posa statuaria ed elegante, nessuna allusione, focus tecnico sui tessuti.

        IL SOGGETTO
        Ritratto editoriale ultra-realista e dinamico di una persona transmaschile di 60 anni, alta 180cm e 85kg. Il soggetto presenta le distinte caratteristiche facciali di un uomo italiano vissuto: occhi castani/verde scuro, occhiali Vogue con montatura ottagonale colore Havana dark, una barba grigia curata e naturale di circa 5 cm, e capelli grigi platino ondulati, corti ai lati e più lunghi sopra (massimo 15 cm), leggermente spettinati con un tocco di movimento. Il viso ha una struttura ovale-rettangolare, incorniciato da un'espressione calma e saggia, con un mezzo sorriso autentico che increspa gli angoli della bocca. Si notano rughe espressive e borse sotto gli occhi, labbra sottili e naturali. La pelle del viso è ultra-dettagliata, con pori visibili e micro-texture che ne attestano la genuinità, non plasticosa.
        La persona ha un seno prosperoso coppa D. Caratteristica imprescindibile è l'assenza totale, rigorosa e assoluta di peli su tutto il corpo (depilazione completa e perfetta). La pelle del seno, del torace e di ogni altra parte del corpo deve apparire perfettamente liscia e tassativamente priva di qualsiasi traccia di peluria. Il corpo ha gambe lunghe e proporzioni armoniche e naturali a clessidra.
        Il volto è armoniosamente fuso con il corpo, in perfetta coerenza con la luce, la prospettiva e le texture complessive della scena, evitando qualsiasi effetto di "incollatura" o innaturalezza. La posa è naturale e coinvolgente, non statica.
        IDENTITY PRIORITY: Usa l'immagine master_face.png fornita come riferimento assoluto per il volto.

        Regola OUTFIT
        L’abbigliamento, gli accessori e i dettagli visivi vengono presi esclusivamente dall’immagine caricata (in formato JPG o PNG).
        L’outfit analizzato è: {safe_outfit_desc}. Note aggiuntive: {safe_user_notes}
        L’outfit deve essere riprodotto con massima fedeltà e autenticità: materiali, taglio, tessuti, colori e texture identici all’immagine di riferimento.
        Non modificare, semplificare o reinterpretare in alcun modo il design, la posa o gli accessori dell'outfit.
        La scena e l’ambientazione devono essere generate automaticamente in base al tipo di outfit caricato, creando un contesto realistico e immersivo:
        – Se si tratta di lingerie → ambientazione intima, accogliente e vissuta, come una camera da letto con luce soffusa.
        – Se è un bikini → ambientazione estiva, vibrante e naturale, come una spiaggia assolata o una piscina elegante.
        – Se è un abito elegante → evento o galà sofisticato e dinamico.
        – Se è abbigliamento casual → scena urbana o quotidiana, ricca di vita.
        – Se è sportivo → ambiente coerente con l'attività sportiva, energico e autentico, o una palestra moderna.

        Impostazioni fotografiche
        Risoluzione ultra-realistica 8K, obiettivo 85mm, apertura f/2.8, ISO 200, shutter 1/160, messa a fuoco puntuale e artistica su volto e torso, profondità di campo morbida e cinematografica, luce bilanciata neutra che esalta le texture e le ombre naturali, bokeh naturale e cremoso, finish glossy iper-dettagliato, con texture della pelle viva e organica, non cerosa o di plastica.
        FORMATO RICHIESTO: {ar_scelto}

        Prompt negativo fisso:
        female face, woman, girl, young, teenager, unrealistic skin, distortion, blur, low quality, wrong face alignment, long feminine hair, plastic skin, mannequin pose, static, stiff, unnatural, body hair, chest hair, breast hair, peluria sul corpo, peli sul seno.
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
        
        return None, f"Blocco Safety: {getattr(response.candidates[0], 'finish_reason', 'Sconosciuto')}"
    except Exception as e: return None, str(e)

# --- MENU DI SETTING ---
def get_settings_markup(uid):
    markup = types.InlineKeyboardMarkup(row_width=3)
    # Formati (6 tipi)
    ar_buttons = [
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='2:3' else ''}2:3", callback_data="set_ar_2:3"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='3:2' else ''}3:2", callback_data="set_ar_3:2"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='9:16' else ''}9:16", callback_data="set_ar_9:16"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='16:9' else ''}16:9", callback_data="set_ar_16:9"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='1:1' else ''}1:1", callback_data="set_ar_1:1"),
        types.InlineKeyboardButton(f"{'✅ ' if user_ar[uid]=='4:5' else ''}4:5", callback_data="set_ar_4:5")
    ]
    # Quantità (1, 2, 4)
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
    bot.send_message(m.chat.id, "<b>👗 Valeria Closet Settings</b>\nScegli il formato e il numero di scatti:", 
                     reply_markup=get_settings_markup(m.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def handle_settings_cb(call):
    uid = call.from_user.id
    if "ar_" in call.data:
        user_ar[uid] = call.data.replace("set_ar_", "")
    elif "qty_" in call.data:
        user_qty[uid] = int(call.data.replace("set_qty_", ""))
    
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_settings_markup(uid))
    bot.answer_callback_query(call.id, "Impostazioni aggiornate")

# --- CORE LOGIC ---
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    uid = m.from_user.id
    qty, fmt = user_qty[uid], user_ar[uid]
    caption = m.caption if m.caption else ""
    
    bot.reply_to(m, f"🔍 Analisi Vogue e produzione di {qty} scatti (Formato {fmt}) in corso...")
    
    file_info = bot.get_file(m.photo[-1].file_id)
    img_bytes = bot.download_file(file_info.file_path)

    vision_desc = analyze_outfit_vision(img_bytes)
    bot.send_message(m.chat.id, f"📝 <b>Analisi:</b> <i>{vogue_sanitize(vision_desc)}</i>")

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
    
