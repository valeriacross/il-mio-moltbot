import os, telebot, html, threading, flask, json, io, logging, time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types as genai_types
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAZIONE LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE ---
VERSION = "5.0.1"
TOKEN = os.environ.get("TELEGRAM_TOKEN_CLOSET")
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
executor = ThreadPoolExecutor(max_workers=4)

# --- CARICAMENTO MASTER FACE ---
def get_face_part():
    try:
        if os.path.exists("master_face.png"):
            with open("master_face.png", "rb") as f:
                data = f.read()
            logger.info("✅ Master Face caricata correttamente.")
            return genai_types.Part.from_bytes(data=data, mime_type="image/png")
        logger.warning("⚠️ Master Face NON TROVATA. Il bot userà solo il testo.")
        return None
    except Exception as e:
        logger.error(f"❌ Errore caricamento master_face: {e}")
        return None

MASTER_PART = get_face_part()

# --- BLOCCHI VALERIA CROSS ---
B1 = "BLOCK 1: REFERENCE 1 (if present) is the Face Identity. REFERENCE 2 is the Outfit/Environment base."
B2 = "BLOCK 2 (Subject): Italian transmasculine Valeria Cross. Body: feminine, Cup D, 180cm, 85kg. Face: Male, 60yo, Beard: silver. Glasses: thin octagonal Vogue Havana."
B3 = "BLOCK 3 (Action): MANDATORY: Keep the EXACT OUTFIT from REFERENCE 2. Apply the SCENE instructions from the text prompt while maintaining character consistency. POSE & EXPRESSION: Generate a completely new pose and facial expression — natural, editorial, confident. Do NOT replicate the pose from the reference image. If the reference shows a mannequin, flat lay or object, invent a natural standing or dynamic pose. Use the reference ONLY for outfit, environment and lighting."
B4 = "BLOCK 4 (Style): 8K, cinematic, 85mm. Watermark: 'feat. Valeria Cross 👠' (bottom center/left)."
NEG = "NEGATIVE PROMPTS: female face, smooth skin, body hair, masculine body shape, flat chest."

# --- TRADUZIONE AUTOMATICA IN INGLESE ---
def translate_to_english(text):
    """Traduce il testo in inglese se non lo è già. Usa Gemini Flash per velocità."""
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                f"Detect the language of the following text. "
                f"If it is already in English, return it exactly as-is. "
                f"If it is in any other language, translate it to English faithfully, "
                f"preserving all formatting, structure, bullet points and technical details. "
                f"Return only the translated text, no explanations.\n\n{text}"
            ]
        )
        if response.text:
            translated = response.text.strip()
            logger.info(f"🌐 Testo tradotto in inglese ({len(translated)} chars)")
            return translated
        return text
    except Exception as e:
        logger.warning(f"⚠️ Traduzione fallita, uso testo originale: {e}")
        return text

# --- PREVIEW PROMPT (con chunking automatico) ---
def send_prompt_preview(chat_id, reply_to_msg_id, header, full_prompt, markup):
    """Invia il prompt completo spezzato in chunks se supera il limite Telegram."""
    CHUNK = 3800
    if len(full_prompt) <= CHUNK:
        # Prompt corto: tutto in un messaggio con i bottoni
        bot.send_message(chat_id,
            f"{header}<code>{html.escape(full_prompt)}</code>\n\nProcedere?",
            reply_to_message_id=reply_to_msg_id,
            reply_markup=markup,
            parse_mode="HTML")
    else:
        # Prompt lungo: chunks senza bottoni, poi messaggio finale con bottoni
        chunks = [full_prompt[i:i+CHUNK] for i in range(0, len(full_prompt), CHUNK)]
        for idx, chunk in enumerate(chunks):
            if idx == 0:
                bot.send_message(chat_id,
                    f"{header}<code>{html.escape(chunk)}</code>",
                    reply_to_message_id=reply_to_msg_id,
                    parse_mode="HTML")
            else:
                bot.send_message(chat_id,
                    f"<i>({idx+1}/{len(chunks)})</i>\n<code>{html.escape(chunk)}</code>",
                    parse_mode="HTML")
        # Messaggio finale con bottoni
        bot.send_message(chat_id,
            f"📋 Prompt completo ({len(chunks)} parti). Procedere?",
            reply_markup=markup,
            parse_mode="HTML")


# FIX: uso uid (user id) invece di cid (chat id) per correttezza per-utente
user_settings = defaultdict(lambda: {'ratio': '2:3', 'count': 1})
pending_prompts = {}

# Traccia le immagini generate dal bot: {message_id: {'prompt': ..., 'img': ...}}
# Usato per la funzione reply-to-modify
generated_images = {}

# --- KEYBOARD ---
def get_formato_keyboard(uid):
    current = user_settings[uid]
    markup = InlineKeyboardMarkup()
    riga1 = ["2:3", "3:4", "4:5", "9:16", "2:1"]
    riga2 = ["3:2", "4:3", "5:4", "16:9", "3:1"]
    markup.row(*[InlineKeyboardButton(f"✅ {r}" if current['ratio'] == r else r, callback_data=f"ar_{r}") for r in riga1])
    markup.row(*[InlineKeyboardButton(f"✅ {r}" if current['ratio'] == r else r, callback_data=f"ar_{r}") for r in riga2])
    return markup

def get_settings_keyboard(uid):
    current = user_settings[uid]
    markup = InlineKeyboardMarkup()
    btns = [InlineKeyboardButton(f"✅ {c}" if current['count'] == c else str(c), callback_data=f"n_{c}") for c in [1, 2, 3, 4]]
    markup.row(*btns)
    return markup

# --- COMANDI ---
@bot.message_handler(commands=['start', 'reset'])
def cmd_start(m):
    uid = m.from_user.id
    username = m.from_user.username or m.from_user.first_name
    user_settings[uid] = {'ratio': '2:3', 'count': 1}
    logger.info(f"🔄 /start da {username} (id={uid}) — settings resettati")
    bot.send_message(m.chat.id,
        f"<b>👠 CLOSET v{VERSION}</b>\n\n"
        f"Pronto per l'indossaggio digitale.\n"
        f"1. Carica una foto dell'abito.\n"
        f"2. Aggiungi nel testo cosa vuoi modificare (es. 'Aggiungi la luna').")

@bot.message_handler(commands=['formato'])
def cmd_formato(m):
    uid = m.from_user.id
    username = m.from_user.username or m.from_user.first_name
    logger.info(f"📐 /formato da {username} (id={uid})")
    bot.send_message(m.chat.id, "📐 <b>Scegli il Formato</b>", reply_markup=get_formato_keyboard(uid))

@bot.message_handler(commands=['settings'])
def cmd_settings(m):
    uid = m.from_user.id
    username = m.from_user.username or m.from_user.first_name
    logger.info(f"⚙️ /settings da {username} (id={uid})")
    bot.send_message(m.chat.id, "🖼️ <b>Quantità Foto</b>", reply_markup=get_settings_keyboard(uid))

@bot.message_handler(commands=['help'])
def cmd_help(m):
    uid = m.from_user.id
    username = m.from_user.username or m.from_user.first_name
    logger.info(f"❓ /help da {username} (id={uid})")
    bot.send_message(m.chat.id,
        f"<b>👠 CLOSET — Guida rapida</b>\n\n"
        f"<b>Come si usa:</b>\n"
        f"Invia una foto dell'abito con una didascalia opzionale per modificare la scena.\n"
        f"Oppure invia solo testo per una generazione senza riferimento outfit.\n\n"
        f"<b>Comandi:</b>\n"
        f"/start o /reset — reimposta le preferenze\n"
        f"/formato — scegli il formato immagine\n"
        f"/settings — scegli la quantità di foto\n"
        f"/help — questa guida\n"
        f"/info — versione e stato del bot")

@bot.message_handler(commands=['info'])
def cmd_info(m):
    uid = m.from_user.id
    username = m.from_user.username or m.from_user.first_name
    logger.info(f"ℹ️ /info da {username} (id={uid})")
    master_status = "✅ Caricata" if MASTER_PART else "⚠️ Non trovata"
    settings = user_settings[uid]
    bot.send_message(m.chat.id,
        f"<b>ℹ️ CLOSET Info</b>\n\n"
        f"Versione: <b>{VERSION}</b>\n"
        f"Master face: {master_status}\n"
        f"Formato attuale: <b>{settings['ratio']}</b>\n"
        f"Quantità attuale: <b>{settings['count']}</b>")

# --- CALLBACK ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    uid = call.from_user.id
    username = call.from_user.username or call.from_user.first_name
    data = call.data

    if data.startswith("ar_"):
        new_ratio = data.split("_")[1]
        user_settings[uid]['ratio'] = new_ratio
        logger.info(f"⚙️ {username} (id={uid}) → formato: {new_ratio}")
        bot.answer_callback_query(call.id, f"✅ Formato: {new_ratio}")
        try:
            bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=get_formato_keyboard(uid))
        except Exception as e:
            logger.warning(f"⚠️ Impossibile aggiornare markup formato: {e}")

    elif data.startswith("n_"):
        new_count = int(data.split("_")[1])
        user_settings[uid]['count'] = new_count
        logger.info(f"⚙️ {username} (id={uid}) → quantità: {new_count}")
        bot.answer_callback_query(call.id, f"✅ Quantità: {new_count}")
        try:
            bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=get_settings_keyboard(uid))
        except Exception as e:
            logger.warning(f"⚠️ Impossibile aggiornare markup settings: {e}")

    elif data == "confirm_gen":
        try:
            bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except Exception as e:
            logger.warning(f"⚠️ Impossibile rimuovere markup conferma: {e}")

        pdata = pending_prompts.get(uid)
        if not pdata:
            logger.warning(f"⚠️ Nessun pending_prompt per {username} (id={uid})")
            bot.send_message(cid, "⚠️ Sessione scaduta. Invia di nuovo la foto o il testo.")
            return

        count = pdata['count']
        logger.info(f"🚀 {username} (id={uid}) → generazione | qty={count} | ratio={user_settings[uid]['ratio']}")
        bot.send_message(cid,
            f"🧶 <b>Sartoria in corso...</b>\n"
            f"📸 Sto creando <b>{count}</b> foto...\n"
            f"⏳ Tempo stimato: ~{count * 20}–{count * 35} secondi. Attendi.")

        def run_task(idx):
            t_start = time.time()
            logger.info(f"   🎨 Scatto {idx+1}/{count} per {username}...")
            img, err = execute_generation(pdata['full_p'], pdata['img'])
            elapsed = round(time.time() - t_start, 1)
            if img:
                try:
                    sent = bot.send_document(cid, io.BytesIO(img),
                        visible_file_name=f"closet_{idx+1}.jpg",
                        caption=f"✅ Scatto {idx+1}/{count} — {elapsed}s\n↩️ <i>Rispondi a questo messaggio per modificarlo</i>")
                    # Salva prompt e immagine per eventuale reply
                    generated_images[sent.message_id] = {
                        'prompt': pdata['full_p'],
                        'img': img
                    }
                    logger.info(f"   ✅ Scatto {idx+1}/{count} inviato a {username} in {elapsed}s (msg_id={sent.message_id})")
                except Exception as e:
                    logger.error(f"   ❌ Errore invio scatto {idx+1} a {username}: {e}")
                    bot.send_message(cid, f"❌ Scatto {idx+1}: generato ma errore nell'invio.\n<code>{html.escape(str(e))}</code>")
            else:
                logger.warning(f"   ❌ Scatto {idx+1}/{count} fallito per {username} ({elapsed}s): {err}")
                bot.send_message(cid, f"❌ <b>Scatto {idx+1} fallito</b> ({elapsed}s)\n{err}")

        for i in range(count):
            executor.submit(run_task, i)
        pending_prompts.pop(uid, None)

    elif data == "cancel_gen":
        try:
            bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except Exception as e:
            logger.warning(f"⚠️ Impossibile rimuovere markup annulla: {e}")
        logger.info(f"❌ {username} (id={uid}) ha annullato.")
        bot.send_message(cid, "❌ <b>Annullato.</b>")
        pending_prompts.pop(uid, None)

# --- MOTORE DI GENERAZIONE ---
def execute_generation(prompt, outfit_img):
    try:
        contents = [prompt]
        if MASTER_PART:
            contents.append(MASTER_PART)
        else:
            logger.warning("⚠️ Generazione senza MASTER_PART.")
        if outfit_img:
            try:
                contents.append(genai_types.Part.from_bytes(data=outfit_img, mime_type="image/jpeg"))
            except Exception as e:
                logger.error(f"❌ Errore preparazione immagine outfit: {e}")
                return None, "❌ Errore nel processare l'immagine allegata."

        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=genai_types.ImageConfig(image_size="2K"),
                safety_settings=[{"category": c, "threshold": "BLOCK_NONE"} for c in
                                  ["HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_HATE_SPEECH",
                                   "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            )
        )

        if not response.candidates:
            logger.warning("⚠️ API: nessun candidato nella risposta.")
            return None, "❌ L'API non ha restituito risultati. Riprova."

        can = response.candidates[0]
        if can.finish_reason != "STOP":
            logger.warning(f"⚠️ Generazione bloccata: {can.finish_reason}")
            return None, f"🛡️ Generazione bloccata.\nMotivo: <b>{can.finish_reason}</b>"

        for p in can.content.parts:
            if p.inline_data:
                return p.inline_data.data, None

        logger.warning("⚠️ Nessuna immagine nelle parti della risposta.")
        return None, "❌ Nessuna immagine nella risposta. Riprova."

    except Exception as e:
        logger.error(f"❌ Crash generazione: {e}", exc_info=True)
        return None, f"❌ Errore interno:\n<code>{html.escape(str(e))}</code>"

# --- HANDLER INPUT ---
@bot.message_handler(content_types=['text', 'photo'])
def handle_input(m):
    cid = m.chat.id
    uid = m.from_user.id
    username = m.from_user.username or m.from_user.first_name

    # --- GESTIONE REPLY A IMMAGINE GENERATA ---
    if m.reply_to_message and m.reply_to_message.message_id in generated_images:
        replied_id = m.reply_to_message.message_id
        original = generated_images[replied_id]
        new_instruction = m.text or m.caption

        if not new_instruction or not new_instruction.strip():
            bot.reply_to(m, "⚠️ Scrivi l'istruzione di modifica nel testo del reply.")
            return

        logger.info(f"↩️ Reply da {username} (id={uid}) su msg {replied_id}: «{new_instruction[:80]}»")

        settings = user_settings[uid]
        # Combina il prompt originale con la nuova istruzione
        new_prompt = (
            f"{original['prompt']}\n\n"
            f"MODIFICATION REQUEST: {new_instruction}\n"
            f"FORMAT: {settings['ratio']}"
        )
        pending_prompts[uid] = {
            'full_p': new_prompt,
            'count': settings['count'],
            'img': original['img']  # usa l'immagine generata come nuovo riferimento
        }

        header = f"↩️ <b>Modifica</b> | 📐 <b>{settings['ratio']}</b> | 🔢 <b>{settings['count']} foto</b>\n\n"
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🚀 CONFERMA", callback_data="confirm_gen"),
            InlineKeyboardButton("❌ ANNULLA", callback_data="cancel_gen")
        )
        send_prompt_preview(m.chat.id, m.message_id, header, new_prompt, markup)
        return

    img_data = None
    if m.content_type == 'photo':
        try:
            file_info = bot.get_file(m.photo[-1].file_id)
            img_data = bot.download_file(file_info.file_path)
            logger.info(f"🖼️ Foto ricevuta da {username} (id={uid}), {len(img_data)} bytes")
        except Exception as e:
            logger.error(f"❌ Errore download foto da {username}: {e}")
            bot.reply_to(m, "❌ Errore nel scaricare la foto. Riprova.")
            return
        if m.caption and m.caption.strip():
            user_instruction = translate_to_english(m.caption)
        else:
            user_instruction = "Maintain the exact scene from the reference."
    else:
        user_instruction = m.text
        if not user_instruction or not user_instruction.strip():
            bot.reply_to(m, "⚠️ Invia una foto dell'abito o scrivi una scena.")
            return
        user_instruction = translate_to_english(user_instruction)

    logger.info(f"✏️ Input da {username} (id={uid}): «{user_instruction[:80]}{'...' if len(user_instruction) > 80 else ''}»")

    settings = user_settings[uid]
    final_p = f"{B1}\n\n{B2}\n\n{B3}\n\nSCENE/DESTINATION: {user_instruction}\nFORMAT: {settings['ratio']}\n\n{B4}\n\n{NEG}"
    pending_prompts[uid] = {'full_p': final_p, 'count': settings['count'], 'img': img_data}

    has_photo = "✅ Sì" if img_data else "❌ No"
    header = f"👗 <b>Outfit:</b> {has_photo} | 📐 <b>{settings['ratio']}</b> | 🔢 <b>{settings['count']} foto</b>\n\n"
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🚀 CONFERMA", callback_data="confirm_gen"),
        InlineKeyboardButton("❌ ANNULLA", callback_data="cancel_gen")
    )
    send_prompt_preview(m.chat.id, m.message_id, header, final_p, markup)

# --- SERVER ---
app = flask.Flask(__name__)

@app.route('/')
def health():
    return f"Closet v{VERSION} Online"

if __name__ == "__main__":
    logger.info(f"🟢 Avvio CLOSET Bot v{VERSION}")
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
