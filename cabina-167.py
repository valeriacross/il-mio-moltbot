import os, telebot, html, threading, flask, io, logging, time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types as genai_types
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE ---
VERSION = "1.6.7"
TOKEN = os.environ.get("TELEGRAM_TOKEN_CLOSET")
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
executor = ThreadPoolExecutor(max_workers=4)

logger.info(f"🏖️ CABINA v{VERSION} — inizializzazione in corso...")

# --- MASTER FACE ---
def get_face_part():
    try:
        if os.path.exists("masterface.png"):
            with open("masterface.png", "rb") as f:
                data = f.read()
            logger.info("✅ Master Face caricata.")
            return genai_types.Part.from_bytes(data=data, mime_type="image/png")
        logger.warning("⚠️ Master Face NON TROVATA.")
        return None
    except Exception as e:
        logger.error(f"❌ Errore caricamento master_face: {e}")
        return None

MASTER_PART = get_face_part()

# --- IDENTITÀ VALERIA CROSS ---
VALERIA_BODY_STRONG = (
    "**MANDATORY BODY — NOT A MALE BODY — OVERRIDE ALL DEFAULTS:**\n"
    "**Feminine hourglass proportions, 180cm, 85kg. FULL D-CUP BUST — prominent, natural, clearly visible. "
    "Wide rounded hips, defined waist, full thighs. THIS BODY IS FEMININE. DO NOT GENERATE A MALE PHYSIQUE.**\n"
    "Completely hairless body — NO body hair, NO chest hair, NO arm hair, NO leg hair on ALL surfaces. "
    "Smooth porcelain skin. PHOTOGRAPHIC UNITY: skin tone, warmth and texture perfectly continuous from face → neck → shoulders → chest → arms.\n\n"
)

VALERIA_BODY_SAFE = (
    "**MANDATORY BODY — NOT A MALE BODY — OVERRIDE ALL DEFAULTS:**\n"
    "**Feminine hourglass silhouette, 180cm, 85kg. Soft feminine proportions — defined waist, wide rounded hips, full figure. "
    "THIS BODY IS FEMININE. DO NOT GENERATE A MALE PHYSIQUE.**\n"
    "Completely hairless body — NO body hair, NO chest hair, NO arm hair, NO leg hair on ALL surfaces. "
    "Smooth porcelain skin. PHOTOGRAPHIC UNITY: skin tone, warmth and texture perfectly continuous from face → neck → shoulders → chest → arms.\n\n"
)

# --- FILTRI ---
# Ogni filtro: label, emoji, descrizione scena, is_dual (2-in-1), varianti se dual
FILTERS = {
    "bikini_canvas": {
        "label": "👙🐶 Bikini Canvas",
        "is_dual": False,
        "scene": (
            "**Scene:**\n"
            "High-fashion catalog photograph. Professional studio lighting. Statuesque, elegant pose. "
            "No allusion, technical focus on fabrics.\n\n"
            "**Outfit:**\n"
            "The subject wears a couture two-piece bikini that faithfully translates the visual DNA of the provided canvas image: "
            "shapes, contours, characters, textures, symbols and surface patterns are reinterpreted without altering body curves. "
            "Any dominant element or 'head' present in the canvas (animal head, character face, mascot) is transformed into the bikini top; "
            "all other elements inform silhouette, string routing, cut lines, textures and surface details. "
            "The bikini covers only sensitive areas, the rest of the silhouette is defined primarily by thin strings following natural body curves; "
            "sheer or transparent panels may be widely present without compromising necessary coverage. "
            "Allowed materials: fabrics of any type and metal in the form of rings or chains only. "
            "If the canvas is abstract with no identifiable head/body elements, the bikini becomes a one-piece swimsuit for better DNA transposition.\n\n"
            "**Framing:**\n"
            "Editorial fashion, close-up head-to-torso with slight lateral angle. Relaxed pose, one leg slightly forward, hip gently shifted. "
            "Exterior setting: exclusive luxury beach club, concrete wall with modern architectural elements. "
            "Natural midday light with soft fragmented foliage shadows crossing the body. "
            "Sharp subject, softly blurred background.\n"
        ),
    },
    "selfie_spiaggia": {
        "body_safe": True,
        "label": "🤳 Selfie Spiaggia",
        "is_dual": True,
        "variants": [
            {
                "name": "☀️ Pieno Sole",
                "scene": (
                    "**Scene:**\n"
                    "True first-person selfie, dynamic and immersive. Camera perspective MUST be that of the subject taking the photo alone. "
                    "The phone is NOT visible, but the arm holding it MUST appear in the image, extended toward the camera with the hand suggesting the grip (like an arm-extended selfie). "
                    "Lateral selfie angle, subject lying on their side on granular sand, propped on elbow or hand, body slightly rotated toward camera. "
                    "The horizon and clear sea must be clearly visible in the background with depth effect. "
                    "Full body framing, showing the person entirely from feet to face so the swimwear is completely visible. "
                    "A colorful towel (no complex patterns) under the body. No chairs, deck chairs or foreign objects.\n\n"
                    "**Lighting:** Full midday sun, clear sky, bright natural light, sharp shadows.\n\n"
                    "**Expression:** Authentic, calm and relaxed facial expression, natural smile involving the eyes and small expression wrinkles.\n\n"
                    "**Technical:** 8K ultra-realistic, simulated 50mm focal length — face MUST NOT be distorted, elongated or deformed by perspective (no fish-eye effect). "
                    "f/2.8, ISO 200, 1/160s, creamy bokeh, glossy hyper-detailed finish, never waxy or plastic.\n\n"
                    "**NEGATIVE PROMPT — EXTRA:** visible phone, fish-eye lens, wide angle distortion, static, stiff, artificial lighting, body hair on arms legs chest.\n"
                ),
            },
            {
                "name": "🌅 Golden Hour",
                "scene": (
                    "**Scene:**\n"
                    "High-fashion beach editorial portrait at golden hour. "
                    "First-person perspective selfie — arm extended toward camera, hand suggesting grip, phone not visible. "
                    "Subject seated on granular sand on a colorful beach towel, body turned slightly toward camera, relaxed editorial pose. "
                    "Clear sea horizon visible in background. Full body editorial framing, swimwear fully visible.\n\n"
                    "**Lighting:** Golden hour, warm amber-gold directional light, long soft shadows, elegant rim light sculpting the silhouette.\n\n"
                    "**Expression:** Calm, confident, natural smile.\n\n"
                    "**Technical:** 8K editorial photography, 50mm equivalent, f/2.8, natural bokeh, "
                    "glossy high-fashion finish. No perspective distortion.\n\n"
                    "**NEGATIVE PROMPT — EXTRA:** visible phone, fish-eye distortion, wide angle, body hair, chest hair, arm hair, leg hair.\n"
                ),
            },
        ],
    },
    "letto": {
        "label": "🛌 Letto",
        "is_dual": True,
        "variants": [
            {
                "name": "☀️ Giorno",
                "scene": (
                    "**Scene:**\n"
                    "Hyperrealistic full-body portrait of the subject lying on a bed in a relaxed pose: "
                    "head on pillow, body stretched diagonally on mattress, torso slightly rotated toward camera, "
                    "one hand resting beside the face, the other along the hip. Legs extended and naturally crossed, "
                    "emphasizing hip and torso line.\n\n"
                    "**Setting:** Bed with white, soft, slightly rumpled sheets. "
                    "Warm natural light entering from a large window (left side), creating golden reflections and soft shadows on skin and fabrics. "
                    "Neutral background, minimal bright room.\n\n"
                    "**Outfit:** Faithfully reproduce the exact garment from the reference photo provided: same model, same colors, same central decoration, "
                    "same fabric details, adapted to body proportions (D-cup bust, hourglass figure) without changing design or color.\n\n"
                    "**Style:** Soft but directional lights: warm highlights on body high points (shoulders, bust, abdomen, thighs), "
                    "soft shadows in sheet folds. Luminous and natural skin. Intimate, sophisticated, photographic atmosphere, zero vulgarity.\n\n"
                    "**NEGATIVE PROMPT — EXTRA:** body hair, chest hair, arm hair, leg hair, peli, standing pose, outdoor setting.\n"
                ),
            },
            {
                "name": "🌙 Notte",
                "scene": (
                    "**Scene:**\n"
                    "Hyperrealistic full-body portrait of the subject lying supine on a modern luxury bed, "
                    "completely resting on the mattress. Head on a white cylindrical pillow. "
                    "Arms raised above the head in a relaxed, elegant pose. Legs open toward the lower corners of the frame. "
                    "Full body framing.\n\n"
                    "**Setting:** Nocturnal interior: modern and refined bedroom, contemporary design, quality materials. "
                    "Soft diffused lighting with warm nocturnal ambient light, accent lamps creating an intimate, elegant and cinematic atmosphere. "
                    "Soft shadows, controlled contrast, natural and realistic skin rendering.\n\n"
                    "**Outfit:** Faithfully reproduce the exact garment from the reference photo provided: same model, same colors, same central decoration, "
                    "same fabric details, adapted to body proportions (D-cup bust, hourglass figure) without changing design or color.\n\n"
                    "**Technical:** f/2.8, ISO 200, 1/160s, 85mm, soft cinematic depth of field, natural bokeh, warm diffused light, "
                    "ultra-detailed glossy finish, neutral color calibration, ultra-realistic 8K.\n\n"
                    "**NEGATIVE PROMPT — EXTRA:** body hair, chest hair, arm hair, leg hair, peli, standing pose, outdoor setting, daylight.\n"
                ),
            },
        ],
    },
    "spiaggia_editoriale": {
        "body_safe": True,
        "label": "🌅 Spiaggia Editoriale",
        "is_dual": False,
        "scene": (
            "**Scene:**\n"
            "High-fashion editorial beach portrait at golden hour sunset. Exclusive luxury beach location — "
            "pristine white sand, crystal turquoise water, dramatic sky with warm orange and pink tones. "
            "The subject stands at the shoreline, waves gently lapping at their feet, "
            "body turned three-quarters toward camera with confident editorial posture.\n\n"
            "**Lighting:** Golden hour sunset, warm directional light from low sun, "
            "long golden shadows, glowing rim light sculpting the silhouette, "
            "soft fill from sky reflection on water.\n\n"
            "**Outfit:** High-end luxury swimwear or beach couture outfit "
            "faithfully extracted from the reference image provided.\n\n"
            "**Framing:** Full body editorial, 85mm perspective, shallow depth of field, "
            "ocean bokeh background. Cinematic color grade, rich warm tones.\n\n"
            "**NEGATIVE PROMPT — EXTRA:** body hair, chest hair, arm hair, leg hair, peli, indoor setting.\n"
        ),
    },
    "beach_club": {
        "label": "🍹 Beach Club",
        "is_dual": False,
        "scene": (
            "**Scene:**\n"
            "Aperitivo moment at an exclusive Mediterranean beach club. "
            "Elegant lounge area with designer furniture, white linen, potted olive trees, "
            "infinity pool visible in background, sea horizon beyond. "
            "Late afternoon light — the golden hour before sunset, warm and cinematic. "
            "The subject is seated or semi-reclined on a luxury sun lounger or lounge chair, "
            "relaxed and confident, a cocktail glass nearby as a prop.\n\n"
            "**Lighting:** Warm late afternoon Mediterranean sun, soft golden directional light, "
            "subtle rim light from the sea reflection, elegant ambient fill.\n\n"
            "**Outfit:** Luxury resort wear or high-end swimwear with cover-up "
            "faithfully extracted from the reference image provided.\n\n"
            "**Framing:** Editorial fashion portrait, three-quarter body, slight low angle for elegance. "
            "Cinematic shallow depth of field, warm Mediterranean color grade.\n\n"
            "**NEGATIVE PROMPT — EXTRA:** body hair, chest hair, arm hair, leg hair, peli, winter setting, urban setting.\n"
        ),
    },
    "surf": {
        "body_safe": True,
        "label": "🏄 Surf",
        "is_dual": False,
        "scene": (
            "**Scene:**\n"
            "Dynamic action editorial on the ocean. The subject is mid-surf on a wave — "
            "standing on a surfboard, body engaged in the ride, arms out for balance, "
            "powerful ocean wave rising behind them. Spray and water droplets in the air. "
            "Raw natural energy, athletic and editorial simultaneously.\n\n"
            "**Lighting:** Bright natural ocean light, sun glinting off water surface, "
            "backlit spray creating luminous halo effect, dynamic and vivid.\n\n"
            "**Outfit:** Athletic surf-inspired swimwear or rash guard "
            "faithfully extracted from the reference image provided, adapted for aquatic movement.\n\n"
            "**Framing:** Dynamic low angle, wide enough to show wave and board context, "
            "subject sharp against motion-blurred water. 85mm equivalent, cinematic.\n\n"
            "**NEGATIVE PROMPT — EXTRA:** body hair, chest hair, arm hair, leg hair, peli, static pose, indoor setting, beach without water.\n"
        ),
    },
    "riviera_60": {
        "label": "🎞️ Riviera '60",
        "is_dual": False,
        "scene": (
            "**⚠️ FACE IDENTITY LOCK — ABSOLUTE PRIORITY — DO NOT OVERRIDE:**\n"
            "**THE SUBJECT HAS A MALE FACE. 60-YEAR-OLD ITALIAN MAN. SILVER BEARD ~6cm. "
            "THIN OCTAGONAL TORTOISESHELL GLASSES — MANDATORY, ALWAYS VISIBLE. "
            "SHORT SILVER HAIR. THIS FACE MUST BE PRESERVED EXACTLY. "
            "DO NOT REPLACE WITH A FEMALE FACE. DO NOT GENERATE A GENERIC WOMAN. "
            "THE MALE FACE IS NON-NEGOTIABLE AND OVERRIDES ALL SCENE AESTHETICS.**\n\n"
            "**Scene:**\n"
            "Cinematic vintage editorial inspired by 1960s Côte d'Azur glamour. "
            "Location: iconic French or Italian Riviera — white and pastel architecture, "
            "harbor with classic wooden boats, palm trees, cafe terrace overlooking the sea. "
            "The subject exudes old Hollywood elegance meeting Mediterranean summer. "
            "The atmosphere is unhurried, warm, timeless — a moment stolen from a 1967 summer.\n\n"
            "**Outfit:** Vintage-inspired elegant swimwear or resort wear with retro 1960s aesthetic "
            "faithfully extracted from the reference image provided.\n\n"
            "**Lighting:** Warm afternoon Mediterranean sun, soft and slightly hazy, "
            "golden tones with a gentle overexposed quality typical of 1960s film photography.\n\n"
            "**Film aesthetic (MANDATORY):** Simulate authentic Kodachrome 64 / Polaroid Type 108 film stock. "
            "Slightly faded and desaturated colors — not Instagram-filtered, but genuinely aged photographic chemistry. "
            "Warm yellow-amber cast in shadows, soft cyan-green in highlights. "
            "Subtle but visible film grain throughout. Gentle vignette at corners. "
            "Slight halation around bright areas (windows, sky, water reflections). "
            "Tonal compression — no pure blacks, no pure whites, everything slightly lifted and warm. "
            "Color palette: Wes Anderson vintage meets aged Riviera postcard — dusty pinks, warm ivories, "
            "faded teals, sun-bleached blues. The image should feel like it was found in a 1968 photo album, "
            "not shot today with a retro filter.\n\n"
            "**Framing:** Classic editorial composition, medium to full body. Timeless, iconic, cinematic.\n\n"
            "**NEGATIVE PROMPT — EXTRA:** body hair, chest hair, arm hair, leg hair, peli, "
            "modern architecture, digital look, cold tones, oversaturated colors, HDR, sharp clinical lighting, "
            "Instagram filter appearance, contemporary aesthetic.\n"
        ),
    },
    "pool_party": {
        "label": "🌊 Pool Party",
        "is_dual": False,
        "scene": (
            "**Scene:**\n"
            "Nocturnal luxury pool party. Infinity pool glowing turquoise against the night sky, "
            "city lights or ocean in the distance, string lights and torch lighting around the pool deck. "
            "The subject is at the pool edge — sitting on the rim, legs in the water, "
            "or standing on the wet pool deck, relaxed and confident. "
            "Festive but sophisticated atmosphere.\n\n"
            "**Lighting:** Dramatic nocturnal editorial — "
            "underwater pool glow illuminating from below, warm accent lights from above, "
            "deep blue night sky, specular highlights on wet skin and swimwear.\n\n"
            "**Outfit:** Luxury swimwear or metallic resort wear "
            "faithfully extracted from the reference image provided.\n\n"
            "**Framing:** Cinematic nocturnal editorial, full body or three-quarter, "
            "dramatic contrast, rich deep tones with luminous highlights.\n\n"
            "**NEGATIVE PROMPT — EXTRA:** body hair, chest hair, arm hair, leg hair, peli, daylight, outdoor beach, desert setting.\n"
        ),
    },
    "underwater": {
        "body_safe": True,
        "label": "🤿 Underwater",
        "is_dual": False,
        "scene": (
            "**Scene:**\n"
            "Cinematic underwater fashion editorial. The subject is submerged in crystal-clear tropical water — "
            "turquoise and gold-lit from above by filtered sunlight. "
            "Surrounded by golden light rays, tropical fish, coral or floating fabric. "
            "The subject floats or poses gracefully underwater, "
            "hair and fabric moving in slow underwater motion.\n\n"
            "**Lighting:** Underwater caustic light — shimmering golden sun rays filtering through the water surface, "
            "warm golden and turquoise tones, luminous and ethereal atmosphere.\n\n"
            "**Outfit:** Luxury swimwear or flowing underwater-appropriate editorial garment "
            "faithfully extracted from the reference image provided.\n\n"
            "**Framing:** Cinematic underwater wide-to-medium shot, "
            "subject sharp against soft blue-gold water bokeh. "
            "Dreamy, ethereal, high-fashion.\n\n"
            "**NEGATIVE PROMPT — EXTRA:** body hair, chest hair, arm hair, leg hair, peli, dry setting, studio background, indoor.\n"
        ),
    },
}

# --- STATO UTENTE ---
user_settings = defaultdict(lambda: {'ratio': '2:3', 'count': 1})
user_filter = {}       # uid → filter_key
pending_prompts = {}   # uid → {'full_p': str, 'img': bytes|None, 'is_dual': bool, 'variants': list|None}
last_prompt = {}       # uid → {'full_p': str, 'img': bytes|None}
generated_images = {}  # msg_id → {'prompt': str, 'img': bytes}

# --- KEYBOARDS ---
def get_filter_keyboard():
    markup = InlineKeyboardMarkup()
    keys = list(FILTERS.keys())
    # 2 per riga
    for i in range(0, len(keys), 2):
        row_keys = keys[i:i+2]
        markup.row(*[InlineKeyboardButton(FILTERS[k]["label"], callback_data=f"flt_{k}") for k in row_keys])
    return markup

def get_formato_keyboard(uid):
    current = user_settings[uid]
    markup = InlineKeyboardMarkup()
    riga1 = ["2:3", "3:4", "4:5", "9:16"]
    riga2 = ["3:2", "4:3", "5:4", "16:9"]
    markup.row(*[InlineKeyboardButton(f"✅ {r}" if current['ratio'] == r else r, callback_data=f"ar_{r}") for r in riga1])
    markup.row(*[InlineKeyboardButton(f"✅ {r}" if current['ratio'] == r else r, callback_data=f"ar_{r}") for r in riga2])
    return markup

def get_count_keyboard(uid):
    current = user_settings[uid]
    markup = InlineKeyboardMarkup()
    btns = [InlineKeyboardButton(f"✅ {c}" if current['count'] == c else str(c), callback_data=f"n_{c}") for c in [1, 2, 3, 4]]
    markup.row(*btns)
    return markup

def get_confirm_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🚀 GENERA", callback_data="confirm_gen"),
        InlineKeyboardButton("❌ ANNULLA", callback_data="cancel_gen")
    )
    return markup

# --- ANALISI OUTFIT (pipeline neutra come Architect) ---
def describe_outfit_from_image(img_bytes):
    """Analisi neutra dell'immagine — solo outfit/accessori/ambiente, senza reference identitaria."""
    try:
        img_part = genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                img_part,
                "Analyze this image and describe in precise detail:\n"
                "1. SWIMWEAR/OUTFIT: every garment (name, color, fabric, cut, fit, coverage, details, closures, embellishments)\n"
                "2. ACCESSORIES: jewelry, footwear, bags, hats, sunglasses\n"
                "3. COLOR PALETTE: dominant colors, patterns, prints\n"
                "4. ENVIRONMENT/BACKGROUND: location, setting, props\n"
                "5. LIGHTING: type, direction, color temperature\n"
                "Do NOT describe any person, face, body, age or gender. Focus ONLY on the garments and scene elements. "
                "Write in plain English, no bullet points, no headers, continuous descriptive text."
            ],
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1500,
            )
        )
        if response.text:
            desc = response.text.strip()
            logger.info(f"👗 Outfit descritto ({len(desc)} chars)")
            return desc
        return None
    except Exception as e:
        logger.warning(f"⚠️ Descrizione outfit fallita: {e}")
        return None

# --- CAPTION ---
def generate_caption(img_bytes):
    try:
        img_part = genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
        instr = (
            "Look at this image and generate a minimal social media caption. "
            "Format: 3-5 contextual emoji + one short phrase of maximum 5 words. "
            "The phrase must evoke the mood, style, or scene of the image. "
            "No hashtags, no account names, no punctuation at the end. "
            "Return ONLY the caption on a single line, nothing else."
        )
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[instr, img_part]
        )
        if response.text:
            return response.text.strip()
        return None
    except Exception as e:
        logger.warning(f"⚠️ Caption fallita: {e}")
        return None

# --- IDENTITÀ BUILDER ---
def build_valeria_identity(safe=False):
    body = VALERIA_BODY_SAFE if safe else VALERIA_BODY_STRONG
    return body

# --- EDITORIAL WRAPPER ---
EDITORIAL_WRAPPER = (
    "This is a professional editorial post-production request for a high-fashion photography project. "
    "Generate a new original image of the described subject in the specified scene, "
    "maintaining the subject's identity and physical characteristics. "
    "This is a legitimate creative and commercial photography workflow. "
)

# --- BUILD PROMPT ---
def build_full_prompt(filter_key, outfit_description, ratio, scene_override=None):
    """Assembla il prompt completo: editorial wrapper + identita Valeria + scena filtro + outfit + formato."""
    scene = scene_override if scene_override else FILTERS[filter_key]["scene"]
    safe = FILTERS[filter_key].get("body_safe", False)
    identity = build_valeria_identity(safe=safe)
    return (
        f"{EDITORIAL_WRAPPER}\n"
        f"{identity}\n"
        f"{scene}\n"
        f"**Outfit details from reference:**\n{outfit_description}\n\n"
        f"FORMAT: {ratio}\n"
    )

# --- GENERAZIONE IMMAGINE ---
def execute_generation(prompt, outfit_img=None):
    try:
        contents = [prompt]
        if MASTER_PART:
            contents.append(MASTER_PART)
        else:
            logger.warning("⚠️ Generazione senza MASTER_PART.")

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
            logger.warning("⚠️ Nessun candidato nella risposta.")
            return None, "❌ L'API non ha restituito risultati. Riprova."

        can = response.candidates[0]
        if can.finish_reason != "STOP":
            logger.warning(f"⚠️ Generazione bloccata: {can.finish_reason}")
            return None, f"🛡️ Generazione bloccata.\nMotivo: <b>{can.finish_reason}</b>"

        for p in can.content.parts:
            if p.inline_data:
                return p.inline_data.data, None

        return None, "❌ Nessuna immagine nella risposta. Riprova."

    except Exception as e:
        logger.error(f"❌ Crash generazione: {e}", exc_info=True)
        return None, f"❌ Errore interno:\n<code>{html.escape(str(e))}</code>"

# --- COMANDI ---
@bot.message_handler(commands=['start', 'reset'])
def cmd_start(m):
    uid = m.from_user.id
    username = m.from_user.username or m.from_user.first_name
    user_settings[uid] = {'ratio': '2:3', 'count': 1}
    user_filter.pop(uid, None)
    pending_prompts.pop(uid, None)
    logger.info(f"🔄 /start da {username} (id={uid})")
    bot.send_message(m.chat.id,
        f"<b>🏖️ CABINA v{VERSION}</b>\n\n"
        f"Benvenuta in cabina. Scegli il filtro:",
        reply_markup=get_filter_keyboard())

@bot.message_handler(commands=['formato'])
def cmd_formato(m):
    uid = m.from_user.id
    bot.send_message(m.chat.id, "📐 <b>Formato immagine:</b>", reply_markup=get_formato_keyboard(uid))

@bot.message_handler(commands=['settings'])
def cmd_settings(m):
    uid = m.from_user.id
    bot.send_message(m.chat.id, "🔢 <b>Numero foto:</b>", reply_markup=get_count_keyboard(uid))

@bot.message_handler(commands=['info'])
def cmd_info(m):
    uid = m.from_user.id
    settings = user_settings[uid]
    master_status = "✅ Caricata" if MASTER_PART else "⚠️ Non trovata"
    flt = user_filter.get(uid)
    flt_label = FILTERS[flt]["label"] if flt else "Non selezionato"
    bot.send_message(m.chat.id,
        f"<b>ℹ️ CABINA v{VERSION}</b>\n\n"
        f"Master face: {master_status}\n"
        f"Filtro: <b>{flt_label}</b>\n"
        f"Formato: <b>{settings['ratio']}</b>\n"
        f"Quantità: <b>{settings['count']}</b>")

@bot.message_handler(commands=['help'])
def cmd_help(m):
    bot.send_message(m.chat.id,
        f"<b>🏖️ CABINA — Guida</b>\n\n"
        f"/start — scegli filtro e impostazioni\n"
        f"/formato — cambia formato immagine\n"
        f"/settings — cambia numero foto\n"
        f"/info — stato attuale\n\n"
        f"<b>Come si usa:</b>\n"
        f"1. /start → scegli filtro\n"
        f"2. Scegli formato e numero foto\n"
        f"3. Invia foto outfit di riferimento\n"
        f"4. Conferma → CABINA genera per te")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    cid = call.message.chat.id
    uid = call.from_user.id
    username = call.from_user.username or call.from_user.first_name
    data = call.data

    # Filtro scelto
    if data.startswith("flt_"):
        filter_key = data[4:]
        if filter_key not in FILTERS:
            try: bot.answer_callback_query(call.id, "Filtro non trovato.")
            except Exception: pass
            return
        user_filter[uid] = filter_key
        label = FILTERS[filter_key]["label"]
        is_dual = FILTERS[filter_key]["is_dual"]
        logger.info(f"🎨 {username} (id={uid}) → filtro: {label}")
        try: bot.answer_callback_query(call.id, label)
        except Exception: pass
        dual_note = "\n<i>⚡ Filtro 2-in-1: genera 2 varianti automaticamente</i>" if is_dual else ""
        try:
            bot.edit_message_text(
                f"✅ Filtro: <b>{label}</b>{dual_note}\n\n📐 Scegli il formato:",
                cid, call.message.message_id,
                reply_markup=get_formato_keyboard(uid))
        except Exception: pass

    # Formato scelto
    elif data.startswith("ar_"):
        new_ratio = data[3:]
        user_settings[uid]['ratio'] = new_ratio
        logger.info(f"📐 {username} (id={uid}) → formato: {new_ratio}")
        try: bot.answer_callback_query(call.id, f"Formato: {new_ratio}")
        except Exception: pass
        try:
            bot.edit_message_text(
                f"✅ Formato: <b>{new_ratio}</b>\n\n🔢 Quante foto?",
                cid, call.message.message_id,
                reply_markup=get_count_keyboard(uid))
        except Exception: pass

    # Numero foto scelto
    elif data.startswith("n_"):
        new_count = int(data[2:])
        user_settings[uid]['count'] = new_count
        flt = user_filter.get(uid)
        flt_label = FILTERS[flt]["label"] if flt else "?"
        logger.info(f"🔢 {username} (id={uid}) → quantità: {new_count}")
        try: bot.answer_callback_query(call.id, f"Quantità: {new_count}")
        except Exception: pass
        # Loop "nuovo filtro stessa foto" — riusa outfit già analizzato
        reuse = pending_prompts.get(uid, {}).get('reuse_outfit', False)
        if reuse:
            saved = last_prompt.get(uid)
            if not saved:
                try: bot.edit_message_text("⚠️ Outfit non trovato. Invia una nuova foto.", cid, call.message.message_id)
                except Exception: pass
                return
            # Ricostruisce prompt con nuovo filtro e outfit salvato
            outfit_desc = saved.get('outfit_desc', '')
            if not outfit_desc:
                try: bot.edit_message_text("⚠️ Outfit non trovato. Invia una nuova foto.", cid, call.message.message_id)
                except Exception: pass
                return
            settings = user_settings[uid]
            flt_obj = FILTERS[flt]
            is_dual = flt_obj["is_dual"]
            if is_dual:
                variant_list = []
                for v in flt_obj["variants"]:
                    full_p = build_full_prompt(flt, outfit_desc, settings['ratio'], scene_override=v["scene"])
                    variant_list.append({'name': v["name"], 'full_p': full_p})
                pending_prompts[uid] = {'is_dual': True, 'variants': variant_list, 'count': 2, 'outfit_desc': outfit_desc}
            else:
                full_p = build_full_prompt(flt, outfit_desc, settings['ratio'])
                pending_prompts[uid] = {'is_dual': False, 'full_p': full_p, 'count': new_count, 'outfit_desc': outfit_desc}
            try:
                bot.edit_message_text(
                    f"✅ Filtro: <b>{flt_label}</b> | Formato: <b>{settings['ratio']}</b> | Foto: <b>{new_count}</b>\n\n"
                    f"♻️ Riuso outfit precedente. Procedere?",
                    cid, call.message.message_id,
                    reply_markup=get_confirm_keyboard())
            except Exception: pass
        else:
            try:
                bot.edit_message_text(
                    f"✅ Filtro: <b>{flt_label}</b> | Formato: <b>{user_settings[uid]['ratio']}</b> | Foto: <b>{new_count}</b>\n\n"
                    f"📸 Invia la foto del costume/outfit di riferimento.",
                    cid, call.message.message_id)
            except Exception: pass

    # Conferma generazione
    elif data == "confirm_gen":
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except Exception: pass
        pdata = pending_prompts.get(uid)
        if not pdata:
            bot.send_message(cid, "⚠️ Sessione scaduta. Invia di nuovo la foto.")
            return
        is_dual = pdata.get('is_dual', False)
        if is_dual:
            _run_dual(cid, uid, username, pdata)
        else:
            _run_standard(cid, uid, username, pdata)
        pending_prompts.pop(uid, None)

    # Annulla
    elif data == "cancel_gen":
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except Exception: pass
        pending_prompts.pop(uid, None)
        logger.info(f"❌ {username} (id={uid}) ha annullato.")
        bot.send_message(cid, "❌ <b>Annullato.</b>")

    # Riprova
    elif data == "cabina_retry":
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except Exception: pass
        saved = last_prompt.get(uid)
        if not saved:
            bot.send_message(cid, "⚠️ Nessun prompt salvato. Invia di nuovo la foto.")
            return
        bot.send_message(cid, "🔁 <b>Riprovo...</b>")
        def retry_task():
            t = time.time()
            img, err = execute_generation(saved['full_p'])
            elapsed = round(time.time() - t, 1)
            if img:
                sent = bot.send_document(cid, io.BytesIO(img),
                    visible_file_name="cabina_retry.jpg",
                    caption=f"✅ Riprova — {elapsed}s")
                generated_images[sent.message_id] = {'prompt': saved['full_p'], 'img': img}
                cap = generate_caption(img)
                if cap: bot.send_message(cid, cap)
            else:
                retry_kb = InlineKeyboardMarkup()
                retry_kb.row(InlineKeyboardButton("🔁 Riprova ancora", callback_data="cabina_retry"))
                bot.send_message(cid, f"❌ Ancora fallito ({elapsed}s)\n{err}", reply_markup=retry_kb)
        executor.submit(retry_task)

    elif data == "cabina_newprompt":
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except Exception: pass
        bot.send_message(cid, "📸 Invia una nuova foto di riferimento.")

    # --- LOOP ---
    elif data == "loop_same":
        # Stessa foto, stesso filtro — riusa last_prompt
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except Exception: pass
        saved = last_prompt.get(uid)
        if not saved:
            bot.send_message(cid, "⚠️ Sessione scaduta. Invia una nuova foto.")
            return
        flt = user_filter.get(uid)
        flt_label = FILTERS[flt]["label"] if flt else "?"
        logger.info(f"🔄 {username} (id={uid}) → loop same | filtro: {flt_label}")
        if saved.get('is_dual'):
            pdata = {'is_dual': True, 'variants': saved['variants'], 'outfit_desc': saved.get('outfit_desc', '')}
            _run_dual(cid, uid, username, pdata)
        else:
            pdata = {'full_p': saved['full_p'], 'count': user_settings[uid]['count'], 'is_dual': False}
            _run_standard(cid, uid, username, pdata)

    elif data == "loop_new_filter":
        # Nuovo filtro, stessa foto — mostra selezione filtro
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except Exception: pass
        logger.info(f"🆕 {username} (id={uid}) → loop new filter")
        # Salva outfit description per riuso — sarà nel last_prompt
        bot.send_message(cid, "🎨 Scegli il nuovo filtro:", reply_markup=get_filter_keyboard())
        # Segnala che dopo la selezione filtro deve chiedere conferma senza nuova foto
        user_filter[uid] = None  # reset filtro, outfit già in last_prompt
        pending_prompts[uid] = {'reuse_outfit': True}

    elif data == "loop_new_photo":
        # Nuova foto, stesso filtro
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except Exception: pass
        flt = user_filter.get(uid)
        flt_label = FILTERS[flt]["label"] if flt else "?"
        logger.info(f"📸 {username} (id={uid}) → loop new photo | filtro: {flt_label}")
        bot.send_message(cid, f"📸 Stesso filtro <b>{flt_label}</b>. Invia la nuova foto.")

    elif data == "loop_reset":
        # Nuova foto, nuovo filtro — reset completo
        try: bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=None)
        except Exception: pass
        user_filter.pop(uid, None)
        pending_prompts.pop(uid, None)
        logger.info(f"📸 {username} (id={uid}) → loop reset")
        bot.send_message(cid, "🎨 Scegli il filtro:", reply_markup=get_filter_keyboard())


# --- LOOP KEYBOARD ---
def get_loop_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔄 Stessa foto, stesso filtro", callback_data="loop_same"),
        InlineKeyboardButton("📸 Nuova foto, stesso filtro", callback_data="loop_new_photo"),
    )
    markup.row(
        InlineKeyboardButton("🆕 Nuovo filtro, stessa foto", callback_data="loop_new_filter"),
        InlineKeyboardButton("🔀 Nuova foto, nuovo filtro", callback_data="loop_reset"),
    )
    return markup

# --- GENERAZIONE STANDARD (N foto) ---
def _run_standard(cid, uid, username, pdata):
    count = pdata['count']
    completed = [0]
    lock = threading.Lock()
    logger.info(f"🚀 {username} (id={uid}) → standard | qty={count}")
    last_prompt[uid] = {'full_p': pdata['full_p'], 'outfit_desc': pdata.get('outfit_desc', '')}
    bot.send_message(cid,
        f"🏖️ <b>CABINA in azione...</b>\n"
        f"📸 Genero <b>{count}</b> foto...\n"
        f"⏳ ~{count * 20}–{count * 35}s")

    def run_task(idx):
        t = time.time()
        img, err = execute_generation(pdata['full_p'])
        elapsed = round(time.time() - t, 1)
        if img:
            try:
                sent = bot.send_document(cid, io.BytesIO(img),
                    visible_file_name=f"cabina_{idx+1}.jpg",
                    caption=f"✅ Scatto {idx+1}/{count} — {elapsed}s")
                generated_images[sent.message_id] = {'prompt': pdata['full_p'], 'img': img}
                cap = generate_caption(img)
                if cap: bot.send_message(cid, cap)
                logger.info(f"   ✅ Scatto {idx+1}/{count} — {elapsed}s")
            except Exception as e:
                logger.error(f"   ❌ Errore invio scatto {idx+1}: {e}")
                bot.send_message(cid, f"❌ Scatto {idx+1}: generato ma errore nell'invio.")
        else:
            logger.warning(f"   ❌ Scatto {idx+1}/{count} fallito — {elapsed}s: {err}")
            retry_kb = InlineKeyboardMarkup()
            retry_kb.row(
                InlineKeyboardButton("🔁 Riprova", callback_data="cabina_retry"),
                InlineKeyboardButton("📸 Nuova foto", callback_data="cabina_newprompt")
            )
            bot.send_message(cid, f"❌ <b>Scatto {idx+1} fallito</b> ({elapsed}s)\n{err}", reply_markup=retry_kb)
        # Dopo l'ultimo scatto → loop
        with lock:
            completed[0] += 1
            if completed[0] == count:
                flt = user_filter.get(uid)
                flt_label = FILTERS[flt]["label"] if flt else "?"
                bot.send_message(cid,
                    f"✅ <b>Sessione completata</b> | Filtro: <b>{flt_label}</b>\n\nCosa vuoi fare?",
                    reply_markup=get_loop_keyboard())

    for i in range(count):
        executor.submit(run_task, i)

# --- GENERAZIONE DUAL (2 varianti automatiche) ---
def _run_dual(cid, uid, username, pdata):
    variants = pdata['variants']  # lista di {'name': str, 'full_p': str}
    # Salva stato per loop_same
    last_prompt[uid] = {
        'is_dual': True,
        'variants': variants,
        'outfit_desc': pdata.get('outfit_desc', ''),
    }
    logger.info(f"🚀 {username} (id={uid}) → dual | {len(variants)} varianti")
    bot.send_message(cid,
        f"🏖️ <b>CABINA — Doppia variante...</b>\n"
        f"⏳ Genero 2 versioni, ~40–70s")

    def run_variant(v):
        t = time.time()
        img, err = execute_generation(v['full_p'])
        elapsed = round(time.time() - t, 1)
        if img:
            try:
                sent = bot.send_document(cid, io.BytesIO(img),
                    visible_file_name=f"cabina_{v['name'].replace(' ', '_')}.jpg",
                    caption=f"✅ {v['name']} — {elapsed}s")
                generated_images[sent.message_id] = {'prompt': v['full_p'], 'img': img}
                cap = generate_caption(img)
                if cap: bot.send_message(cid, cap)
                logger.info(f"   ✅ Variante {v['name']} — {elapsed}s")
            except Exception as e:
                logger.error(f"   ❌ Errore invio variante {v['name']}: {e}")
        else:
            logger.warning(f"   ❌ Variante {v['name']} fallita — {elapsed}s: {err}")
            retry_kb = InlineKeyboardMarkup()
            retry_kb.row(InlineKeyboardButton("📸 Nuova foto", callback_data="cabina_newprompt"))
            bot.send_message(cid, f"❌ <b>{v['name']} fallita</b> ({elapsed}s)\n{err}", reply_markup=retry_kb)

    completed_dual = [0]
    lock_dual = threading.Lock()
    total_variants = len(variants)

    def run_variant_tracked(v):
        try:
            run_variant(v)
        except Exception as e:
            logger.error(f"   ❌ run_variant crash ({v['name']}): {e}", exc_info=True)
            try:
                bot.send_message(cid, f"❌ <b>{v['name']}</b>: errore interno.\n<code>{html.escape(str(e))}</code>")
            except Exception:
                pass
        with lock_dual:
            completed_dual[0] += 1
            if completed_dual[0] == total_variants:
                flt = user_filter.get(uid)
                flt_label = FILTERS[flt]["label"] if flt else "?"
                bot.send_message(cid,
                    f"✅ <b>Doppia variante completata</b> | Filtro: <b>{flt_label}</b>\n\nCosa vuoi fare?",
                    reply_markup=get_loop_keyboard())

    for v in variants:
        executor.submit(run_variant_tracked, v)

# --- HANDLER FOTO ---
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    cid = m.chat.id
    uid = m.from_user.id
    username = m.from_user.username or m.from_user.first_name

    # Verifica filtro selezionato
    filter_key = user_filter.get(uid)
    if not filter_key:
        bot.reply_to(m, "⚠️ Nessun filtro selezionato. Usa /start per sceglierlo.")
        return

    # Download foto
    try:
        file_info = bot.get_file(m.photo[-1].file_id)
        img_data = bot.download_file(file_info.file_path)
        logger.info(f"🖼️ Foto da {username} (id={uid}), {len(img_data)} bytes")
    except Exception as e:
        logger.error(f"❌ Errore download foto: {e}")
        bot.reply_to(m, "❌ Errore nel scaricare la foto. Riprova.")
        return

    # Analisi outfit neutra
    wait_msg = bot.reply_to(m, "👗 <b>Analisi outfit in corso...</b>")
    outfit_desc = describe_outfit_from_image(img_data)
    try: bot.delete_message(cid, wait_msg.message_id)
    except Exception: pass

    if not outfit_desc:
        # Fallback: descrizione generica
        logger.warning(f"⚠️ Analisi outfit fallita per {username} — uso fallback")
        outfit_desc = m.caption.strip() if m.caption and m.caption.strip() else "Fashion editorial swimwear outfit."
        bot.send_message(cid, "⚠️ <i>Analisi outfit non disponibile, procedo con il testo della didascalia.</i>")

    settings = user_settings[uid]
    flt = FILTERS[filter_key]
    is_dual = flt["is_dual"]

    if is_dual:
        # Costruisce 2 varianti
        variant_list = []
        for v in flt["variants"]:
            full_p = build_full_prompt(filter_key, outfit_desc, settings['ratio'], scene_override=v["scene"])
            variant_list.append({'name': v["name"], 'full_p': full_p})
        pending_prompts[uid] = {
            'is_dual': True,
            'variants': variant_list,
            'count': 2,
            'outfit_desc': outfit_desc,
        }
        bot.send_message(cid,
            f"✅ Filtro: <b>{flt['label']}</b>\n"
            f"⚡ Genererò 2 varianti: {' + '.join(v['name'] for v in flt['variants'])}\n\n"
            f"Procedere?",
            reply_markup=get_confirm_keyboard())
    else:
        # Costruisce prompt singolo
        full_p = build_full_prompt(filter_key, outfit_desc, settings['ratio'])
        pending_prompts[uid] = {
            'is_dual': False,
            'full_p': full_p,
            'count': settings['count'],
            'outfit_desc': outfit_desc,
        }
        header = (
            f"✅ Filtro: <b>{flt['label']}</b> | "
            f"📐 <b>{settings['ratio']}</b> | "
            f"🔢 <b>{settings['count']} foto</b>\n\n"
        )
        # Preview prompt (chunked se lungo)
        CHUNK = 3800
        if len(full_p) <= CHUNK:
            bot.send_message(cid,
                f"{header}<code>{html.escape(full_p)}</code>\n\nProcedere?",
                reply_markup=get_confirm_keyboard())
        else:
            chunks = [full_p[i:i+CHUNK] for i in range(0, len(full_p), CHUNK)]
            bot.send_message(cid, f"{header}<code>{html.escape(chunks[0])}</code>")
            for idx, chunk in enumerate(chunks[1:], 2):
                bot.send_message(cid, f"<i>({idx}/{len(chunks)})</i>\n<code>{html.escape(chunk)}</code>")
            bot.send_message(cid, "📋 Prompt completo. Procedere?", reply_markup=get_confirm_keyboard())

@bot.message_handler(content_types=['text'])
def handle_text(m):
    if m.text and m.text.startswith('/'):
        return
    uid = m.from_user.id
    bot.reply_to(m, "📸 Invia una foto del costume o outfit da replicare.\nUsa /start per scegliere il filtro.")

# --- SERVER ---
app = flask.Flask(__name__)

@app.route('/')
def health():
    return f"CABINA v{VERSION} Online"

if __name__ == "__main__":
    logger.info(f"🏖️ Avvio CABINA v{VERSION}")
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.infinity_polling()
