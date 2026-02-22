import os, telebot, html, threading, flask, json, io
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types as genai_types
from io import BytesIO
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAZIONE ---
VERSION = "4.5.1 (Persistent)"
TOKEN = os.environ.get("TELEGRAM_TOKEN_CLOSET")
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
executor = ThreadPoolExecutor(max_workers=2)

# --- CARICAMENTO MASTER FACE ---
def get_face_part():
    try:
        if os.path.exists("master_face.png"):
            with open("master_face.png", "rb") as f:
                return genai_types.Part.from_bytes(data=f.read(), mime_type="image/png")
        return None
    except Exception as e:
        print(f"❌ Errore master_face: {e}")
        return None

MASTER_PART = get_face_part()

# --- BLOCCHI VALERIA CROSS ---
B1 = "BLOCK 1 (Activation & Priority): Reference image has ABSOLUTE PRIORITY. ZERO face drift allowed. Male Italian face identity."
B2 = "BLOCK 2 (Subject & Face): Nameless Italian transmasculine avatar (Valeria Cross). Body: soft feminine, harmonious hourglass, prosperous full breasts (cup D), 180cm, 85kg. Body hairless. FACE: Male Italian face, ~60 years old, ultra-detailed skin (pores, wrinkles, bags). Expression: calm, half-smile, NO teeth. Beard: light grey/silver, groomed, 6–7 cm. Glasses MANDATORY: thin octagonal Vogue, Havana dark."
B3 = "BLOCK 3 (Hair & Technique): HAIR: Light grey/silver. Short elegant Italian style, volume. Nape exposed. Top <15 cm. IMAGE CONCEPT: 8K, cinematic realism. CAMERA: 85mm, f/2.8, ISO 200, 1/160s. Focus on face/torso. Shallow depth of field, natural bokeh."
B4 = "BLOCK 4 (Rendering & Output): RENDERING: Subsurface Scattering, Global Illumination, Fresnel, Frequency separation on skin. Watermark: 'feat. Valeria Cross 👠' (elegant cursive, champagne, bottom center/left, opacity 90%, very small font size)."
NEG = "NEGATIVE PROMPTS: [Face] female/young face, smooth skin, distortion. [Hair] long/medium hair, ponytail, bun, braid. [Body] body/chest/leg hair (peli NO!)."

# --- STATO UTENTE E MENU ---
user_settings = {}
pending_prompts = {}

def get_settings(cid):
    if cid not in user_settings:
        user_settings[cid] = {'ratio': '2:3', 'count': 1}
    return user_settings[cid]

def get_formato_keyboard(cid):
    current = get_settings(cid)
    markup = InlineKeyboardMarkup()
    riga1, riga2 = ["2:3", "3:4", "4:5", "9:16", "2:1"], ["3:2", "4:3", "5:4", "16:9", "3:1"]
    markup.row(*[InlineKeyboardButton(f"✅ {r}" if current['ratio'] == r else r, callback_data=f"ar_{r}") for r in riga1])
    markup.row(*[InlineKeyboardButton(f"✅ {r}" if current['ratio'] == r else r, callback_data=f"ar_{r}") for r in riga2])
    return markup

def get_settings_keyboard(cid):
    current = get_settings(cid)
    markup = InlineKeyboardMarkup()
    btns = [InlineKeyboardButton(f"✅ {c}" if current['count'] == c else str(c), callback_data=f"n_{c}") for c in [1, 2, 3, 4]]
    markup.row(*btns)
    return markup

@bot.message_handler(commands=['start', 'reset', 'formato', 'settings'])
def handle_commands(m):
    cid = m.chat.id
    if m.text.startswith('/start') or m.text.startswith('/reset'):
        user_settings[cid] = {'ratio': '2:3', 'count': 1}
        bot.send_message(cid, f"<b>👠 CLOSET v{VERSION} Online</b>\nDefault: 2:3, 1 Foto.")
    elif m.text.startswith('/formato'):
        bot.send_message(cid, "📐 <b>Scegli il Formato</b>", reply_markup=get_formato_keyboard(cid))
    elif m.text.startswith('/settings'):
        bot.send_message(cid, "🖼️ <b>Scegli le Foto</b>", reply_markup=get_settings_keyboard(cid))

@bot.callback_query_handler(func=lambda call: call.data.startswith(("ar_", "n_", "confirm_", "cancel_")))
def handle_query(call):
    cid = call.message.chat.id
    uid = call.from_user.id
    current = get_settings(cid)
    
    if call.data.startswith("ar_"):
        current['ratio'] = call.data.split("_")[1]
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=get_formato_keyboard(cid))
    elif call.data.startswith("n_"):
        current['count'] = int(call.data.split("_")[1])
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=get_settings_keyboard(cid))
    
    elif call.data == "confirm_gen":
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        data = pending_prompts.get(uid)
        if not data: return
        bot.send_message(cid, "🚀 <b>Generazione avviata...</b>")
        def run_task(idx):
            img, err = execute_generation(data['full_p'], data['img'])
            if img: bot.send_document(cid, io.BytesIO(img), visible_file_name=f"closet_{idx+1}.jpg")
            else: bot.send_message(cid, f"❌ Errore: {err}")
        for i in range(data['count']): executor.submit(run_task, i)
        pending_prompts.pop(uid, None)
        
    elif call.data == "cancel_gen":
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        bot.send_message(cid, "❌ <b>Annullato.</b>")
        pending_prompts.pop(uid, None)

# --- MOTORE ---
def execute_generation(full_prompt, rif_img):
    try:
        contents = [full_prompt, MASTER_PART]
        if rif_img: contents.append(genai_types.Part.from_bytes(data=rif_img, mime_type="image/jpeg"))
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
        if not response.candidates: return None, "No candidates."
        can = response.candidates[0]
        if can.finish_reason != "STOP": return None, f"🛡️ Safety: {can.finish_reason}"
        for p in can.content.parts:
            if p.inline_data: return p.inline_data.data, None
        return None, "Vuoto."
    except Exception as e: return None, str(e)

@bot.message_handler(content_types=['text', 'photo'])
def ask_confirmation(m):
    if m.text and m.text.startswith('/'): return
    cid, uid = m.chat.id, m.from_user.id
    idea = m.caption if m.content_type == 'photo' else m.text
    if not idea: return
    
    img_data = bot.download_file(bot.get_file(m.photo[-1].file_id).file_path) if m.content_type == 'photo' else None
    settings = get_settings(cid)
    
    final_p = f"{B1}\n\n{B2}\n\n{B3}\n\nSCENE: {idea}\nFORMAT: {settings['ratio']}\n\n{B4}\n\n{NEG}"
    pending_prompts[uid] = {'full_p': final_p, 'count': settings['count'], 'img': img_data}

    preview = {"status": "AWAITING", "prompt": final_p, "meta": settings}
    markup = InlineKeyboardMarkup().row(InlineKeyboardButton("🚀 CONFERMA", callback_data="confirm_gen"), 
                                        InlineKeyboardButton("❌ ANNULLA", callback_data="cancel_gen"))
    
    bot.reply_to(m, f"📝 <b>Anteprima Prompt:</b>\n<code>{html.escape(json.dumps(preview, indent=2))}</code>", reply_markup=markup)

# --- SERVER ---
app = flask.Flask(__name__)
@app.route('/')
def health(): return "CLOSET_OK"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
