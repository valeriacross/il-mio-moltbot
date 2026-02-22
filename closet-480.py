import os, telebot, html, threading, flask, json, io
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types as genai_types
from io import BytesIO
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAZIONE ---
VERSION = "4.8 (Ultimate Hybrid)"
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

# --- BLOCCHI VALERIA CROSS (VERSIONE IBRIDA) ---
B1 = "BLOCK 1: REFERENCE 1 is the Face Identity. REFERENCE 2 is the Outfit/Environment base."
B2 = "BLOCK 2 (Subject): Italian transmasculine Valeria Cross. Body: feminine, Cup D, 180cm, 85kg. Face: Male, 60yo, Beard: silver. Glasses: thin octagonal Vogue Havana."
B3 = "BLOCK 3 (Action): MANDATORY: Keep the EXACT OUTFIT from REFERENCE 2. Apply the SCENE instructions (e.g. adding elements like the moon or changing background) while maintaining the character's consistency."
B4 = "BLOCK 4 (Style): 8K, cinematic, 85mm. Watermark: 'feat. Valeria Cross 👠' (bottom center/left)."
NEG = "NEGATIVE PROMPTS: female face, smooth skin, body hair, masculine body shape, flat chest."

# --- STATO UTENTE ---
user_settings = {}
pending_prompts = {}

def get_settings(cid):
    if cid not in user_settings:
        user_settings[cid] = {'ratio': '2:3', 'count': 1}
    return user_settings[cid]

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_gen", "cancel_gen"])
def handle_action(call):
    cid, uid = call.message.chat.id, call.from_user.id
    bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
    if call.data == "confirm_gen":
        data = pending_prompts.get(uid)
        if not data: return
        bot.send_message(cid, "🧶 **Sartoria e ambientazione in corso...**")
        def run_task(idx):
            img, err = execute_generation(data['full_p'], data['img'])
            if img: bot.send_document(cid, io.BytesIO(img), visible_file_name=f"valeria_hybrid_{idx+1}.jpg")
            else: bot.send_message(cid, f"❌ Errore: {err}")
        for i in range(data['count']): executor.submit(run_task, i)
    pending_prompts.pop(uid, None)

def execute_generation(prompt, outfit_img):
    try:
        contents = [prompt, MASTER_PART] # Ref 1
        if outfit_img:
            contents.append(genai_types.Part.from_bytes(data=outfit_img, mime_type="image/jpeg")) # Ref 2
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
        return None, "Errore dati."
    except Exception as e: return None, str(e)

@bot.message_handler(content_types=['photo'])
def handle_closet_hybrid(m):
    cid, uid = m.chat.id, m.from_user.id
    img_data = bot.download_file(bot.get_file(m.photo[-1].file_id).file_path)
    
    # QUI SALVIAMO IL TUO TESTO (LA DESTINAZIONE)
    user_instruction = m.caption if m.caption else "Maintain the exact scene from the photo."
    settings = get_settings(cid)
    
    final_p = f"{B1}\n\n{B2}\n\n{B3}\n\nSCENE/DESTINATION: {user_instruction}\nFORMAT: {settings['ratio']}\n\n{B4}\n\n{NEG}"
    pending_prompts[uid] = {'full_p': final_p, 'count': settings['count'], 'img': img_data}
    
    preview = {"status": "HYBRID_READY", "prompt": final_p}
    markup = InlineKeyboardMarkup().row(InlineKeyboardButton("🚀 CONFERMA", callback_data="confirm_gen"), 
                                        InlineKeyboardButton("❌ ANNULLA", callback_data="cancel_gen"))
    
    bot.reply_to(m, f"👗 **Immagine e Istruzioni acquisite.**\nIl testo '{user_instruction}' verrà usato per modificare la scena.\n\n<code>{html.escape(json.dumps(preview, indent=2))}</code>", reply_markup=markup)

# --- SERVER ---
app = flask.Flask(__name__)
@app.route('/')
def health(): return "CLOSET_OK"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
