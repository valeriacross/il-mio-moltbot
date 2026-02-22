import os, telebot, html, threading, flask, json, io, logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types as genai_types
from io import BytesIO
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAZIONE LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE ---
VERSION = "4.8.2 (Ironclad)"
TOKEN = os.environ.get("TELEGRAM_TOKEN_CLOSET")
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
executor = ThreadPoolExecutor(max_workers=2)

# --- CARICAMENTO MASTER FACE ---
def get_face_part():
    try:
        if os.path.exists("master_face.png"):
            with open("master_face.png", "rb") as f:
                logger.info("✅ Master Face caricata correttamente.")
                return genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
        logger.warning("⚠️ Master Face NON TROVATA. Il bot userà solo il testo.")
        return None
    except Exception as e:
        logger.error(f"❌ Errore caricamento master_face: {e}")
        return None

MASTER_PART = get_face_part()

# --- BLOCCHI VALERIA CROSS ---
B1 = "BLOCK 1: REFERENCE 1 (if present) is the Face Identity. REFERENCE 2 is the Outfit/Environment base."
B2 = "BLOCK 2 (Subject): Italian transmasculine Valeria Cross. Body: feminine, Cup D, 180cm, 85kg. Face: Male, 60yo, Beard: silver. Glasses: thin octagonal Vogue Havana."
B3 = "BLOCK 3 (Action): MANDATORY: Keep the EXACT OUTFIT from REFERENCE 2. Apply the SCENE instructions from the text prompt while maintaining character consistency."
B4 = "BLOCK 4 (Style): 8K, cinematic, 85mm. Watermark: 'feat. Valeria Cross 👠' (bottom center/left)."
NEG = "NEGATIVE PROMPTS: female face, smooth skin, body hair, masculine body shape, flat chest."

# --- STATO UTENTE E MENU ---
user_settings = defaultdict(lambda: {'ratio': '2:3', 'count': 1})
pending_prompts = {}

def get_formato_keyboard(cid):
    current = user_settings[cid]
    markup = InlineKeyboardMarkup()
    riga1, riga2 = ["2:3", "3:4", "4:5", "9:16", "2:1"], ["3:2", "4:3", "5:4", "16:9", "3:1"]
    markup.row(*[InlineKeyboardButton(f"✅ {r}" if current['ratio'] == r else r, callback_data=f"ar_{r}") for r in riga1])
    markup.row(*[InlineKeyboardButton(f"✅ {r}" if current['ratio'] == r else r, callback_data=f"ar_{r}") for r in riga2])
    return markup

def get_settings_keyboard(cid):
    current = user_settings[cid]
    markup = InlineKeyboardMarkup()
    btns = [InlineKeyboardButton(f"✅ {c}" if current['count'] == c else str(c), callback_data=f"n_{c}") for c in [1, 2, 3, 4]]
    markup.row(*btns)
    return markup

# --- HANDLER COMANDI (PRIORITÀ ALTA) ---
@bot.message_handler(commands=['start', 'reset'])
def cmd_start(m):
    cid = m.chat.id
    user_settings[cid] = {'ratio': '2:3', 'count': 1}
    bot.send_message(cid, f"<b>👠 CLOSET v{VERSION}</b>\n\nPronto per l'indossaggio digitale.\n1. Carica una foto dell'abito.\n2. Aggiungi nel testo cosa vuoi modificare (es. 'Aggiungi la luna').")

@bot.message_handler(commands=['formato'])
def cmd_formato(m):
    bot.send_message(m.chat.id, "📐 <b>Scegli il Formato</b>", reply_markup=get_formato_keyboard(m.chat.id))

@bot.message_handler(commands=['settings'])
def cmd_settings(m):
    bot.send_message(m.chat.id, "🖼️ <b>Quantità Foto</b>", reply_markup=get_settings_keyboard(m.chat.id))

# --- HANDLER CALLBACK (BOTTONI) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid, uid = call.message.chat.id, call.from_user.id
    data = call.data
    
    if data.startswith("ar_"):
        user_settings[cid]['ratio'] = data.split("_")[1]
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=get_formato_keyboard(cid))
    elif data.startswith("n_"):
        user_settings[cid]['count'] = int(data.split("_")[1])
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=get_settings_keyboard(cid))
    
    elif data == "confirm_gen":
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        pdata = pending_prompts.get(uid)
        if not pdata: return
        bot.send_message(cid, "🧶 <b>Sartoria in corso...</b>")
        def run_task(idx):
            img, err = execute_generation(pdata['full_p'], pdata['img'])
            if img: bot.send_document(cid, io.BytesIO(img), visible_file_name=f"closet_{idx+1}.jpg")
            else: bot.send_message(cid, f"❌ Errore: {err}")
        for i in range(pdata['count']): executor.submit(run_task, i)
        pending_prompts.pop(uid, None)
        
    elif data == "cancel_gen":
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        bot.send_message(cid, "❌ <b>Annullato.</b>")
        pending_prompts.pop(uid, None)

# --- MOTORE DI GENERAZIONE ---
def execute_generation(prompt, outfit_img):
    try:
        contents = [prompt]
        if MASTER_PART: contents.append(MASTER_PART)
        if outfit_img:
            contents.append(genai_types.Part.from_bytes(data=outfit_img, mime_type="image/jpeg"))
        
        response = client.models.generate_content(
            model="nano-banana-pro-preview",
            contents=contents,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                safety_settings=[{"category": c, "threshold": "BLOCK_NONE"} for c in 
                                 ["HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_HATE_SPEECH", 
                                  "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            )
        )
        can = response.candidates[0]
        if can.finish_reason != "STOP": return None, f"Blocco: {can.finish_reason}"
        for p in can.content.parts:
            if p.inline_data: return p.inline_data.data, None
        return None, "Errore dati Immagine."
    except Exception as e:
        logger.error(f"Crash Generazione: {e}")
        return None, str(e)

# --- HANDLER INPUT (FOTO E TESTO) ---
@bot.message_handler(content_types=['text', 'photo'])
def handle_input(m):
    cid, uid = m.chat.id, m.from_user.id
    
    # Se è una foto
    if m.content_type == 'photo':
        img_data = bot.download_file(bot.get_file(m.photo[-1].file_id).file_path)
        user_instruction = m.caption if m.caption else "Maintain the exact scene from the reference."
    # Se è solo testo
    else:
        img_data = None
        user_instruction = m.text
        
    settings = user_settings[cid]
    final_p = f"{B1}\n\n{B2}\n\n{B3}\n\nSCENE/DESTINATION: {user_instruction}\nFORMAT: {settings['ratio']}\n\n{B4}\n\n{NEG}"
    pending_prompts[uid] = {'full_p': final_p, 'count': settings['count'], 'img': img_data}

    preview = {"status": "HYBRID_READY", "prompt": final_p, "meta": settings}
    markup = InlineKeyboardMarkup().row(InlineKeyboardButton("🚀 CONFERMA", callback_data="confirm_gen"), 
                                        InlineKeyboardButton("❌ ANNULLA", callback_data="cancel_gen"))
    
    bot.reply_to(m, f"📝 <b>Anteprima Prompt:</b>\n<code>{html.escape(json.dumps(preview, indent=2))}</code>", reply_markup=markup)

# --- SERVER ---
app = flask.Flask(__name__)
@app.route('/')
def health(): return "CLOSET_OK"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    logger.info("🚀 Bot in ascolto...")
    bot.infinity_polling()
