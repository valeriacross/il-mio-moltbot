import os, io, threading, logging, flask, telebot, html, time
from telebot import types
from google import genai
from google.genai import types as genai_types
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- VERSIONE ---
VERSION = "3.51"

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE ---
TOKEN = os.environ.get("TELEGRAM_TOKEN_FX")
API_KEY = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-3-pro-image-preview"
MODEL_TEXT_ID = "gemini-3-flash-preview"

# --- STATO UTENTE ---
user_filter   = defaultdict(lambda: None)   # filtro selezionato
user_category = defaultdict(lambda: None)   # categoria selezionata
pending       = {}                          # {uid: {'img': bytes, 'filter_key': str}}
last_img      = {}                          # {uid: bytes} — ultima immagine usata

executor = ThreadPoolExecutor(max_workers=4)

# --- CARICAMENTO MASTER FACE ---
def get_face_part():
    try:
        if os.path.exists("master_face.png"):
            with open("master_face.png", "rb") as f:
                data = f.read()
            logger.info("✅ master_face.png caricata correttamente.")
            return genai_types.Part.from_bytes(data=data, mime_type="image/png")
        logger.warning("⚠️ master_face.png non trovata.")
        return None
    except Exception as e:
        logger.error(f"❌ Errore caricamento master_face: {e}")
        return None

MASTER_PART = get_face_part()

# ============================================================
# FILTRI
# ============================================================

FILTERS = {

    # ── STILISTICI ──────────────────────────────────────────
    "cinematic_highangle": {
        "label": "⬆️⬇️ Cinematic High-Angle",
        "cat": "stylistic",
        "prompt": (
            "Apply a photographic filter. "
            "A cinematic high-angle portrait, looking up at the camera, intense expressive eyes with sharp focus. "
            "Shot from an overhead perspective creating depth and vulnerability, shallow depth of field with softly blurred concrete background, "
            "dramatic soft lighting with subtle shadows, moody color grading, high contrast, ultra-realistic skin tones, "
            "professional fashion photography style, 85mm lens look, f/1.8, cinematic realism, editorial portrait, "
            "8K detail, film grain, modern aesthetic, photorealistic."
        )
    },
    "dramatic": {
        "label": "⬆️ Dramatic Low-Angle",
        "cat": "stylistic",
        "prompt": (
            "Apply a photographic filter with an extreme low-to-high angle, sharply focusing on the foreground. "
            "Dramatically increase contrast and saturation, making colors rich and deep, especially reds and blacks, "
            "while heavily darkening the background to create a dramatic, theatrical effect with bright, direct lighting."
        )
    },
    "glossy": {
        "label": "🌟 Glossy Opal",
        "cat": "stylistic",
        "prompt": (
            "Apply the 'Ultra-Opal Fairy-Angel Couture V2' style: hyper-glamour rendering with 3D iridescent aesthetics, "
            "multi-layered pearlescent reflections, rainbow opalescence and liquid glows reminiscent of fairy wings, "
            "Swarovski crystals and mirror-gloss surfaces. Lighting is extra-luxury: soft, enveloping, with golden-pink "
            "atmospheric scattering, suspended micro-sparkles, clean flares and precious bokeh producing pearlescent bubble spheres. "
            "Every surface is ultra-detailed: ultra-fine glitter, multicolor refractions, wet and metallic highlights, "
            "superior material depth, 'angel couture runway' effect. Only the outfit receives iridescent shifting reflections "
            "with pearl-champagne tone and cold-pink hot spots with blue-opal touches. No effects on skin."
        )
    },
    "iridescent": {
        "label": "🌈 Iridescent",
        "cat": "stylistic",
        "prompt": (
            "Rendered with an extreme iridescent and opalescent finish. The lighting must use dichroic refraction to create "
            "a spectrum of shifting colors between electric teal, deep cosmic blue, and fiery metallic orange. "
            "Surfaces (NOT THE SKIN, ANYWHERE) should have a pearlescent glow with high-gloss textures and micro-crystalline details. "
            "Incorporate prismatic light dispersion and volumetric studio lighting to emphasize sharp edges and intricate decorations. "
            "The color palette is dominated by a high-contrast complementary scheme of burning gold and vibrant cyan. "
            "Every highlight should shimmer with a holographic effect, mimicking the interplay of light on diamonds and silk flowers. "
            "Ultra-high definition, 8K, cinematic fashion aesthetic."
        )
    },
    "rainbow_neon": {
        "label": "🌈🌈 Rainbow Neon",
        "cat": "stylistic",
        "prompt": (
            "Ultra-detailed liquid neon drips and holographic surfaces. Rainbow prisms and sparkles everywhere. "
            "Glamorous fantasy style. Starry cosmic background with intense rainbow light beams cutting through space. "
            "Vibrant neon color palette throughout the scene. "
            "Photography and Rendering: hyper-realistic editorial fantasy photography. Cinematic lighting with dramatic contrast "
            "and neon reflections. Warm and soft light balance with vibrant highlights. "
            "Technical: 85mm, f/2.8, ISO 200, 1/160s. 8K, ultra-detailed, cinematic realism."
        )
    },
    "galaxy": {
        "label": "🌌 Galaxy Couture",
        "cat": "stylistic",
        "prompt": (
            "Apply an exclusive 'jewel galaxy haute couture' aesthetic filter to the uploaded image. "
            "Keep the subject, composition and base shapes of all elements in the photo unchanged; do not add or remove "
            "recognizable elements, limiting modifications to color, texture and lighting. "
            "Reconfigure the palette to midnight blue, purple, turquoise and warm gold, with soft iridescent tones reminiscent "
            "of nebulae and cosmic skies. Add brilliant metallic reflections and colored edge glints to objects, as if coated "
            "in iridescent metal. Introduce small gem and crystal-like lights in amber-orange, aquamarine and opalescent white "
            "tones, only as decorative details on existing surfaces. Enhance contrast and sharpness for extremely detailed textures, "
            "with soft studio lighting emphasizing reflections. Hyper-realistic, fashion cover look, no additional text in image. "
            "Apply the filter only to colors and textures; do not modify object shapes."
        )
    },
    "neon_hdr": {
        "label": "💛 Neon HDR",
        "cat": "stylistic",
        "prompt": (
            "Use this photo as the base and keep the same person, pose, clothing and background. "
            "Transform the lighting so that parts of the hair, clothes and background edges become powerful neon light sources. "
            "Add bright cyan, magenta and lime glow along contours and folds, as if the subject is lit by fiber-optic strands "
            "and LED reflections. Increase saturation and contrast strongly, pushing the glowing areas close to overexposed "
            "like an HDR long-exposure neon photo, while keeping the face and eyes sharp and realistic. "
            "Preserve natural skin texture, pores and wrinkles, and keep all original patterns and shapes of the clothing "
            "and background unchanged. Ultra-realistic, cinematic studio lighting, 4K resolution. "
            "Negative: dim light, weak glow, cartoon, anime, illustration, plastic skin, flat lighting, "
            "new shapes or symbols on clothing, pattern changes, glowing outline only, sticker effect."
        )
    },

    # ── FANTASY & ART ────────────────────────────────────────
    "stained_glass": {
        "label": "🎐 Stained Glass",
        "cat": "fantasy",
        "prompt": (
            "Apply this filter to the image: a hyper-realistic subject made entirely of stained glass and translucent crystal. "
            "The whole body is a mosaic of milky white and pale blue glass tiles, held together by an intricate polished silver wire frame. "
            "Ethereal glowing aquamarine eyes with crystalline details. The hair flows in sculpted waves of transparent teal glass. "
            "Soft cinematic lighting hitting the metallic edges, creating brilliant specular highlights and internal refractions. "
            "Elegant, sculptural, avant-garde art style. Dark moody background, 8K resolution, shot on 85mm lens, "
            "macro photography detail, iridescent textures."
        )
    },
    "underwater": {
        "label": "🧜 Underwater Gold",
        "cat": "fantasy",
        "prompt": (
            "High-fantasy underwater style with high-brilliance gold and saturated turquoise/teal palette, "
            "volumetric lighting from above, translucent flowing fabrics like silk, hyper-detailed jewelry in gold "
            "and turquoise stones, thousands of micro-bubbles and suspended particles, mystical atmosphere in deep "
            "blue-cyan water, ultra-detailed glossy high-contrast rendering with specular reflections."
        )
    },
    "3d_synthetic": {
        "label": "🪟 3D Synthetic",
        "cat": "fantasy",
        "prompt": (
            "Generate a hyper-realistic cutting-edge 3D rendering of the provided image. Transform the subject's material "
            "into a high-quality translucent synthetic material with a dazzling glossy multichromatic finish. Its surface "
            "should feature a subtle knurled texture, precision-engineered to refract light into razor-sharp specular reflections. "
            "The scene is illuminated with a powerful multi-source HDRI studio setup, characterized by intense rim lighting "
            "and backlighting sculpting the form. The dominant color combination is a sophisticated blend of electric cyan, "
            "deep violet and hints of molten gold, creating an energetic yet refined gradient on the material. "
            "Implement pronounced bloom effects, subtle chromatic aberration and a delicate bloom effect to enhance the futuristic aesthetic. "
            "Absolute black background will amplify the subject's radiant luminosity. The camera captures a flat, frontal, "
            "eye-level perspective using a macro lens that subtly warps light at the edges. Ensure the foreground is in sharp focus, "
            "no depth of field effects. Final touches: aggressive contrast enhancement, saturated spectrum color grading "
            "and an almost imperceptible layer of digital grain."
        )
    },
    "graffiti": {
        "label": "🧯 Graffiti Artist",
        "cat": "fantasy",
        "prompt": (
            "Create one ultra-realistic image showing the same person as the reference spray-painting a full-body "
            "self-portrait graffiti on an urban brick wall. The person is standing or half-crouched, mid-spray, "
            "while the entire head-to-toe mural is clearly visible on a single continuous brick wall with realistic texture. "
            "The graffiti looks fresh with natural overspray and paint drips, spray mist is visible, and several unbranded "
            "spray cans lie on the ground. The person's face, body, outfit, and identity remain exactly the same, "
            "with light paint speckles only on clothes or shoes. Lighting is realistic urban daylight, shallow depth of field, "
            "and the final image is high-resolution, clean, and fully realistic with no extra people, text, or fantasy elements."
        )
    },
    "cloud_sculpture": {
        "label": "☁️ Cloud Sculpture",
        "cat": "fantasy",
        "prompt": (
            "Transform the subject in the uploaded photo into a sculptural form composed entirely of soft, atmospheric clouds, "
            "while preserving their recognizable silhouette, posture, and defining features. "
            "The transformation should feel symbolic rather than literal — identity conveyed through shape, expression, "
            "and overall presence rather than surface detail or material substitution. "
            "Build the form from layered cloud volumes with gentle depth, allowing natural light and shadow to define structure. "
            "No skin, no fabric, no physical materials — only cloud. "
            "Lighting: natural sunlight with soft diffused highlights and airy shadows. "
            "Background: bright open blue sky with a subtle top-to-bottom gradient from deep azure to pale horizon. "
            "Mood: ethereal and dreamlike, as if the subject's essence has temporarily taken on an atmospheric form. "
            "Full body visible, centered in frame, high detail on cloud texture and volumetric depth. "
            "Ultra-realistic render quality. No text, no watermark."
        )
    },
    "ghost_temporal": {
        "label": "👻 Ghost Temporal",
        "cat": "stylistic",
        "use_master": False,
        "prompt": (
            "Using the uploaded photo as the identity and style reference, create an ultra-realistic 8K cinematic studio portrait "
            "framed from mid-thigh up. "
            "IDENTITY LOCK: Preserve the exact person from the photo — same face, facial structure, skin tone, hair, outfit. "
            "BACKGROUND: Vibrant ochre-red background (#C0392B), uniform but subtly graded for depth. "
            "OUTFIT: Preserve exactly the outfit worn by the subject in the uploaded photo — same garments, colors, textures, "
            "and any visible accessories. Do not replace or alter the clothing under any circumstance. "
            "POSE: Subject standing confidently, sharp focus, primary figure in full presence. "
            "GHOST EFFECT: A translucent motion-blurred ghost duplicate of the subject positioned slightly behind and to the right, "
            "streaking horizontally with colorful light trails (red, blue, yellow) conveying rapid movement or temporal distortion. "
            "The ghost is semi-transparent, 40-50% opacity, with chromatic aberration streaks. "
            "LIGHTING: Harsh frontal studio lighting, crisp shadows, emphasizing fabric textures. "
            "TECHNICAL: High-fashion editorial style, shallow depth of field on primary figure, 85mm lens feel, "
            "bold experimental avant-garde mood. 8K, ultra-sharp on primary subject. No text, no watermark."
        )
    },

    # ── SCENOGRAFICI ─────────────────────────────────────────
    "giantess": {
        "label": "🏙️ Giantess NYC",
        "cat": "scenic",
        "prompt": (
            "A hyper-realistic photograph of a giant human subject. "
            "SCENARIO: the subject walks carefully down the center of Broadway in New York City, her sneakers spanning several "
            "city blocks while her head towers above the spire of the Chrysler Building. "
            "She is an actual human of colossal proportions (hundreds of meters tall). "
            "The environment is a real-world location with authentic textures of glass, concrete, and foliage. "
            "SUBJECT FIDELITY: exact face from reference photo, perfect facial likeness, real human skin texture, "
            "realistic human body proportions. "
            "ENVIRONMENT FIDELITY: no toys, no diorama, no miniature effect. Sharp focus throughout. "
            "LIGHTING: natural daylight, realistic atmospheric perspective, 8K resolution, shot on professional camera, "
            "extreme high resolution. Tilt-shift effect applied."
        )
    },
    "action_figure": {
        "label": "🪆 Action Figure",
        "cat": "scenic",
        "prompt": (
            "Create a 1/7 scale commercial figure of the character in the image, in a realistic style set in a real environment. "
            "The figure is placed on a computer desk and has a transparent round acrylic base. "
            "Next to the desk appears the real person from the image, life-sized and wearing the same outfit as the figure, "
            "carefully cleaning it with a fine brush, in a modern, well-lit studio. "
            "In the background, a collection of toys and action figures can be seen."
        )
    },
    "art_doll": {
        "label": "👯 Art Doll Exhibition",
        "cat": "scenic",
        "prompt": (
            "In a bright, minimalist art exhibition space, generate an oversized sculpture in the style of a 'cute big-eyed doll', "
            "with clothing style, hairstyle and accessories 100% identical to those of the person in the uploaded photo. "
            "The sculpture is 50% taller than a real person and stands naturally behind and slightly to the side of the person, "
            "ensuring the real person's face and pose do not change at all. "
            "Overall lighting and shadows are soft but well-defined; the image is clear and rich in detail, "
            "creating a cute and trendy exhibition atmosphere. Original proportions maintained."
        )
    },
    "toy_window": {
        "label": "🎎 Toy Store Window",
        "cat": "scenic",
        "prompt": (
            "Generate an ultra-realistic image based exclusively on the uploaded canvas, using its proportions and format. "
            "The scene is a bright, high-end street-fashion photograph. "
            "The subject stands in front of a luxury toy store window, delicately touching the glass with one hand. "
            "Inside the display window there is a full-size cartoon doll modeled on the subject: same features, same hair, "
            "same outfit, but rendered as a cute animated character with large eyes, stylized proportions and a 'cartoon deluxe' mood. "
            "The doll is hyper-defined with premium toy rendering. Realistic reflections on the store window, high-level fashion look, "
            "keeping the subject's real face unchanged. "
            "If the subject is an animal, a doll/puppy of the same animal will be created following the same rules. "
            "Photographic settings: f/2.8, ISO 200, 1/160s, 85mm lens, focus on torso and face, soft cinematic depth of field, "
            "natural bokeh, warm soft light, ultra-detailed glossy finish, 4.2MP output."
        )
    },

    # ── COLLAGE ───────────────────────────────────────────────
    "selfie_stick": {
        "label": "🤳 Selfie Stick POV",
        "cat": "scenic",
        "use_master": False,
        "prompt": (
            "CREATE A COMPLETELY NEW IMAGE — do not recolor, relight or minimally edit the reference. "
            "Generate a brand new scene from scratch using the person's identity from the uploaded photo. "
            "CAMERA SETUP: Extreme wide-angle fisheye POV. The camera is mounted at the top of a selfie stick held by the subject's RIGHT hand. "
            "The camera is the one taking this photo — it cannot appear in the image. "
            "The subject's RIGHT hand grips the bottom of the stick, arm extended upward and forward. "
            "The stick extends upward from the hand and exits the frame at the top — the top of the stick and camera are NOT visible. "
            "The LEFT arm hangs naturally at the side — it does NOT hold anything. "
            "Strong fisheye barrel distortion on the edges. The subject looks up toward the lens with a natural smile. "
            "FRAMING: Bird's eye perspective — subject seen from 2-3 meters above. "
            "The environment extends dramatically in all directions. "
            "Only the bottom portion of the stick (near the hand grip) may be visible at the lower edge of the frame. "
            "IDENTITY LOCK: Preserve 
