import os, io, threading, logging, flask, telebot, html, time
from telebot import types
from google import genai
from google.genai import types as genai_types
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# --- VERSIONE ---
VERSION = "2.0.9"

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE ---
TOKEN = os.environ.get("TELEGRAM_TOKEN_FX")
API_KEY = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-3-pro-image-preview"

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

    # ── VARIANTI ─────────────────────────────────────────────
    "new_pose": {
        "label": "🆕 New Pose",
        "cat": "variants",
        "prompt": (
            "Create a new image using the exact same prompt, scene, outfit and identity as the reference, "
            "but with a completely different, natural and editorial pose and a different facial expression."
        )
    },
    "triple_set": {
        "label": "3️⃣× Triple Set",
        "cat": "variants",
        "prompt": (
            "Generate a set of 3 separate and different images in high resolution, using the uploaded image as base, "
            "changing pose but maintaining its original aspect ratio and exact proportions. Seed: random for each."
        )
    },
    "triptych": {
        "label": "3️⃣❌1️⃣ Triptych GHI",
        "cat": "variants",
        "prompt": (
            "Create a 3:1 collage of three versions with completely different poses and facial expressions of the same prompt, seed: random. "
            "Version 1: Glossy — hyper-glamour rendering, pearlescent iridescent aesthetics, mirror-gloss surfaces, angel couture runway effect. "
            "Version 2: HDR+ — powerful neon light sources along hair, clothes and background edges, cyan, magenta and lime glow, "
            "HDR long-exposure neon style, face and eyes sharp and realistic. "
            "Version 3: Holographic — dichroic refraction spectrum shifting between electric teal, deep cosmic blue and fiery metallic orange, "
            "prismatic light dispersion, holographic shimmer on all non-skin surfaces."
        )
    },
    "collage_2x2": {
        "label": "🟦 Collage 2×2",
        "cat": "variants",
        "prompt": (
            "Create a 2×2 quad-panel collage of the same subject with four completely different camera angles and poses, "
            "all shot in a professional studio with a light seamless cyclorama background. "
            "Each panel has a distinct framing and perspective — no two panels may share the same angle or pose. "
            "Panel top-left (LOW-ANGLE CLOSE): Camera positioned low, angled upward. Subject has one hand on hip, "
            "the other extended toward the lens creating strong depth and perspective distortion. "
            "Panel top-right (OVERHEAD TOP-DOWN): Extreme high-angle bird's eye view looking straight down at the subject. "
            "Subject gazes directly up at the camera, one arm reaching upward, creative proportion distortion. "
            "Panel bottom-left (DUTCH ANGLE FULL BODY): Full-length shot with tilted horizon (Dutch angle). "
            "Subject posed in three-quarter profile highlighting silhouette and outfit structure. "
            "Panel bottom-right (REAR THREE-QUARTER): Shot from behind and slightly to the side. "
            "Subject looks back over the shoulder toward the camera, showing the back of the outfit and full length. "
            "Lighting: professional studio strobe lighting, hard shadows defining body contours and fabric texture. "
            "Consistent subject identity, outfit, and color grade across all four panels. "
            "Thin dark dividing lines between panels. Unified cinematic look."
        )
    },
    "photobooth_4x4": {
        "label": "📷 Photobooth 4×4",
        "cat": "variants",
        "use_master": False,
        "prompt": (
            "Using the uploaded photo as the identity and style reference, create a color photobooth expression grid "
            "with a 4x4 layout of 16 panels. "
            "IDENTITY LOCK: Preserve the exact person from the photo — same face, facial structure, skin tone, hair, "
            "makeup, accessories, jewelry, props and any distinctive elements visible in the image. "
            "If the photo shows makeup, earrings, props (fruit, objects, etc.), wet hair, or any distinctive styling — "
            "replicate all of these consistently across every single panel. "
            "SETTING: Use the same background environment and lighting mood from the reference photo, "
            "adapted to a tight head-and-shoulders photobooth framing. "
            "Eyes sharp in every panel. Natural realistic skin tones. Medium to high contrast. "
            "Subtle authentic analog photobooth grain in color. Thin gutters between panels. High panel consistency. "
            "50mm lens look. Tight head and shoulders framing. "
            "16 expressions in order: 1-scrunched smile eyes slightly squeezed, 2-intense stare fingers framing eyes, "
            "3-big joyful laugh mouth open, 4-bored unimpressed chin in hands, 5-sad pout watery eyes, "
            "6-goofy face hands making small horns above head, 7-playful tongue out cheeky grin, "
            "8-angry glare eyebrows down, 9-flirty look hand touching cheek, 10-surprised wide eyes mouth slightly open, "
            "11-excited shout hands near face, 12-mischievous grin claw-like hand pose, "
            "13-confused frown lips pressed, 14-dramatic crying hands on head, "
            "15-tongue out eyes closed playful, 16-duck face with small devil horns gesture. "
            "Ultra high resolution, photorealistic color photobooth contact sheet aesthetic. "
            "No extra fingers, no missing fingers, no deformed hands, no warped face, no uneven eyes, "
            "no melted mouth, no plastic skin, no text, no watermark, no blur."
        )
    },

    # ── BIKINI SCENES ─────────────────────────────────────────
    "bikini_night": {
        "label": "🌙 Night Lingerie",
        "cat": "bikini",
        "prompt": (
            "Generate an ultra-realistic image based exclusively on the uploaded canvas to determine proportions and format. "
            "Scene: Valeria Cross, Italian transmasculine figure, statuesque hourglass silhouette with generous editorial décolleté, "
            "180cm, 85kg, flawlessly smooth porcelain skin across all surfaces. "
            "Face: strong Italian male face ~60yo, oval-rectangular, ultra-detailed skin texture with pores and wrinkles. "
            "Calm expression, slight natural half-smile. Dark brown/green eyes. "
            "Silver-grey beard, groomed, ~4cm. Mandatory thin octagonal Vogue glasses, Havana dark tortoiseshell. "
            "Hair: short silver Italian cut, voluminous, nape fully exposed, max 10-15cm on top. "
            "Scene: Valeria Cross lying supine on a luxury modern bed, fully resting on the mattress. Head on a cylindrical white pillow. "
            "Arms raised above the head in a relaxed elegant pose. Legs open toward the lower corners of the frame. Full-body shot. "
            "Wearing exactly the outfit shown in the reference image, no variations. "
            "Nighttime interior: modern refined bedroom, contemporary design, premium materials. "
            "Soft ambient lighting with warm accent lamps creating an intimate, elegant and cinematic atmosphere. "
            "Soft shadows, controlled contrast, natural realistic skin rendering. "
            "Camera: f/2.8, ISO 200, 1/160s, 85mm, focus on torso and face, soft cinematic depth of field, "
            "natural bokeh, warm soft light, ultra-detailed glossy finish, 8K. "
            "Negative: female face, young face, plastic skin, wrong face alignment, anatomical distortions, blur, low quality, "
            "long hair, hair touching neck or shoulders, body hair on any surface."
        )
    },
    "bikini_bed": {
        "label": "👙🛌 Bed Editorial",
        "cat": "bikini",
        "prompt": (
            "Fashion catalog photograph, professional studio lighting, statuesque and elegant pose, zero vulgarity, technical focus on fabrics. "
            "Ultra-realistic editorial portrait of an Italian transmasculine figure, exactly 60 years old, 180cm, 85kg. "
            "The subject presents the distinct authentic facial features of a lived Italian man: dark brown/green eyes, "
            "thin octagonal Vogue glasses Havana dark tortoiseshell, natural grey beard ~5cm (not fake or drawn), "
            "and grey-platinum wavy hair, short on the sides and longer on top (max 15cm), slightly disheveled with natural movement. "
            "Oval-rectangular face structure, wise and deeply human expression, authentic half-smile. "
            "Visible expressive wrinkles, natural under-eye depth. Ultra-detailed organic skin with visible pores, "
            "never plastic or waxy. Statuesque hourglass silhouette with generous editorial décolleté. "
            "Flawlessly smooth porcelain skin across all body surfaces — impeccable editorial finish. "
            "Long legs, harmonious natural proportions. Face naturally fused with body in perfect coherence with light, perspective and textures. "
            "Scene: hyper-realistic full-body portrait of the subject lying on a bed in a relaxed pose: head on pillow, "
            "body stretched diagonally on mattress, torso slightly rotated toward camera, one hand resting beside the face, "
            "the other along the hip. Natural relaxed but sensual posture. Legs extended and naturally crossed, emphasizing hip and torso line. "
            "Setting: bed with white sheets, soft and slightly rumpled, warm natural light entering from a large background window (left side), "
            "creating golden reflections and soft shadows on skin and fabrics. Neutral background, minimal bright room. "
            "Outfit: wear EXACTLY the garment from the reference photo: same model, same colors, same decoration, same fabric details, "
            "adapted to the figure's proportions. "
            "Style: soft directional lights with warm highlights on body high points, soft shadows in sheet folds. "
            "Luminous natural skin, light but refined grooming. Intimate, sophisticated, photographic atmosphere, zero vulgarity. "
            "Camera: f/2.8, ISO 200, 1/160s, 85mm, focus on torso and face, soft cinematic depth of field, natural bokeh, 8K. "
            "Negative: female face, young feminine face, cartoon, morphing, smoothing, proportion errors, digital artifacts, anime, "
            "face swap, low quality, long hair, shaved hair, body hair on any surface."
        )
    },
    "bikini_selfie": {
        "label": "👙🤳 Beach Selfie",
        "cat": "bikini",
        "prompt": (
            "Generate an ultra-realistic image in highest resolution, using the uploaded image as canvas and outfit reference, "
            "maintaining its original aspect ratio and exact proportions. "
            "Ultra-realistic editorial portrait of an Italian transmasculine figure, 60 years old, 180cm, 85kg. "
            "The subject presents the distinct facial features of a lived Italian man: thin octagonal Vogue glasses Havana dark tortoiseshell, "
            "natural grey beard ~5cm, silver-platinum hair short on sides and longer on top (max 15cm), slightly disheveled. "
            "Oval-rectangular face, wise and human expression, authentic half-smile with natural eye creases. "
            "Ultra-detailed organic skin with visible pores, never plastic or waxy. "
            "Statuesque hourglass silhouette with generous editorial décolleté. "
            "Flawlessly smooth porcelain skin across all body surfaces — impeccable editorial finish. "
            "Selfie shot: true first-person perspective, the camera viewpoint IS the subject taking the photo. "
            "The phone is NOT visible, but the arm holding it MUST appear in the image, extended toward the camera "
            "with the hand suggesting the grip (arm-extended selfie). "
            "Angle: dynamic natural lateral selfie perspective, subject lying on their side, arm extended. "
            "Horizon and clear sea clearly visible in background with depth effect. Full-body framing, entire person visible "
            "from feet to face so the swimwear is completely visible. "
            "Subject fully lying on grainy sand, resting on one side in a relaxed natural pose, on elbow or hand, "
            "body slightly rotated toward camera for the selfie. The arm holding the phone is visible and extended toward the camera; "
            "the other arm rests relaxed on sand or a colorful vivid towel without complex patterns. "
            "No chairs, deck chairs or foreign objects in scene. "
            "Facial expression: authentic, calm and relaxed, natural smile engaging eyes and small expression wrinkles. "
            "Outfit: extract the swimwear from the reference photo and apply it maintaining absolute fidelity to cut, color, fabric and pattern. "
            "Setting: beach, golden hour, sea in background, colorful towel under the hip. "
            "Camera: 8K, 85mm, f/2.8, ISO 200, 1/160s, focus on face and torso, soft cinematic depth of field, "
            "golden hour illumination, natural creamy bokeh, ultra-detailed glossy finish. "
            "Negative: female face, young, distorted face, fish-eye distortion, plastic skin, beard missing, "
            "wrong glasses, long hair, body hair on any surface, visible phone."
        )
    },
    "bikini_selfie2": {
        "label": "👙🤳2 Beach Selfie v2",
        "cat": "bikini",
        "prompt": (
            "Generate an ultra-realistic image in highest resolution based on the uploaded canvas for format and proportions. "
            "Ultra-realistic editorial portrait of an Italian transmasculine figure, 60 years old. "
            "Face: oval-rectangular structure, lived Italian male traits. Dark brown/green eyes. "
            "Thin octagonal Vogue glasses Havana dark, well-defined, not deformed. "
            "Natural groomed grey beard ~5cm, hipster style. "
            "Silver-platinum slightly wavy hair, short on sides, longer on top (15cm max), combed back with natural movement. "
            "Expression: calm, wise, authentic half-smile, no exaggerated selfie expressions. "
            "Body: hourglass silhouette with generous editorial décolleté, flawlessly smooth porcelain skin across all surfaces, "
            "visible pores, ultra-realistic texture. "
            "Outfit: analyze the uploaded image, extract the swimwear (bikini, trikini, one-piece, etc.) "
            "and apply it to the subject maintaining absolute fidelity to cut, color, fabric and pattern. "
            "Selfie framing with attention to distortion: subject lying on sand (on their side). "
            "Taking a selfie with arm extended upward/forward. "
            "IMPORTANT: use a simulated focal length of 50mm even though it is a selfie. "
            "The face must NOT be distorted, elongated or deformed by perspective (no fish-eye effect). "
            "The arm holding the phone is visible, and flawlessly smooth. "
            "Setting: beach, golden hour, sea in background, colorful towel under the hip. "
            "Camera: 8K, 85mm, f/2.8, ISO 200, 1/160s, soft cinematic depth of field, golden hour light, creamy bokeh. "
            "Negative: female face, woman, distorted face, fish-eye lens, wide angle distortion, plastic skin, "
            "beard missing, wrong glasses, different person, long hair, body hair on any surface."
        )
    },
    "bikini_club": {
        "label": "👙🐶 Beach Club",
        "cat": "bikini",
        "prompt": (
            "Fashion catalog photograph, professional studio lighting, statuesque and elegant pose, zero vulgarity, technical focus on fabrics. "
            "Ultra-realistic dynamic editorial portrait of an Italian transmasculine figure, 60 years old, 180cm, 85kg. "
            "The subject presents the distinct facial features of a lived Italian man: dark brown/green eyes, "
            "thin octagonal Vogue glasses Havana dark tortoiseshell, natural grey beard ~5cm, "
            "and silver-platinum wavy hair, short on sides and longer on top (max 15cm), slightly disheveled with natural movement. "
            "Oval-rectangular face, calm and wise expression, authentic half-smile. "
            "Visible expressive wrinkles and natural under-eye depth. Ultra-detailed organic skin with visible pores, never plastic. "
            "Statuesque hourglass silhouette with generous editorial décolleté. "
            "Flawlessly smooth porcelain skin across all body surfaces — impeccable editorial finish. "
            "Long legs, harmonious natural hourglass proportions. "
            "Outfit: a couture two-piece bikini, form-fitting and fully wearable, designed by rigorously and faithfully translating "
            "the visual DNA of the canvas image: shapes, contours, characters, textures, symbols and surface patterns are reinterpreted "
            "without altering the body's natural curves. Any dominant element or 'head' in the canvas (animal head, character face or mascot) "
            "is transformed into the bikini top pieces; all other elements inform silhouette, string routing, cut lines, textures "
            "and surface details. The bikini covers only sensitive areas, while the rest of the silhouette is defined primarily "
            "by thin strings following the body's natural curves; sheer or transparent panels may be widely present "
            "without compromising necessary coverage. Permitted materials: fabrics of any type and metal in the form of rings or chains. "
            "If the canvas image is abstract with no identifiable head/body elements, the bikini becomes a one-piece swimsuit, "
            "allowing better transposition of the canvas DNA. "
            "Fashion editorial framing: head-to-torso close-up with slight lateral angle, figure in relaxed pose "
            "with one leg slightly forward and hip barely shifted. "
            "Setting: outdoor exclusive luxury beach club, next to a wall of refined exposed concrete with modern architectural elements. "
            "Natural midday light with soft fragmented leaf shadows crossing the body. Sharp defined subject, gently blurred background. "
            "Camera: f/2.8, ISO 200, 1/160s, 85mm, focus on torso and face, soft cinematic depth of field, "
            "natural bokeh, warm soft light, ultra-detailed glossy finish, 8K. "
            "Negative: female face, woman, young, teenager, unrealistic skin, distortion, blur, low quality, "
            "wrong face alignment, long feminine hair, plastic skin, mannequin pose, static, stiff, unnatural, "
            "body hair on any surface."
        )
    },
}

# Categorie e ordine
CATEGORIES = {
    "stylistic": "🎨 Stilistici",
    "fantasy":   "✨ Fantasy & Art",
    "scenic":    "🏙️ Scenografici",
    "variants":  "🔄 Varianti",
    "bikini":    "👙 Bikini Scenes",
}

def filters_by_cat(cat):
    return {k: v for k, v in FILTERS.items() if v["cat"] == cat}

# ============================================================
# BOT
# ============================================================
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- KEYBOARD CATEGORIE ---
def cat_keyboard():
    markup = types.InlineKeyboardMarkup()
    for cat_key, cat_label in CATEGORIES.items():
        markup.add(types.InlineKeyboardButton(cat_label, callback_data=f"cat_{cat_key}"))
    return markup

# --- KEYBOARD FILTRI ---
def filter_keyboard(cat):
    markup = types.InlineKeyboardMarkup()
    for fkey, fdata in filters_by_cat(cat).items():
        markup.add(types.InlineKeyboardButton(fdata["label"], callback_data=f"f_{fkey}"))
    markup.add(types.InlineKeyboardButton("◀️ Indietro", callback_data="back_cats"))
    return markup

# --- /start ---
@bot.message_handler(commands=['start', 'reset'])
def cmd_start(m):
    uid = m.from_user.id
    user_filter[uid] = None
    user_category[uid] = None
    pending.pop(uid, None)
    logger.info(f"🔄 /start da {m.from_user.username or m.from_user.first_name} (id={uid})")
    bot.send_message(m.chat.id,
        f"<b>🎨 ValeriaFX v{VERSION}</b>\n\n"
        f"Invia una foto e scegli un filtro.\n"
        f"Usa /filtro per scegliere il filtro prima della foto, o invia la foto direttamente.",
        reply_markup=cat_keyboard()
    )

# --- /filtro ---
@bot.message_handler(commands=['filtro', 'filter'])
def cmd_filtro(m):
    uid = m.from_user.id
    logger.info(f"🎨 /filtro da {m.from_user.username or m.from_user.first_name} (id={uid})")
    bot.send_message(m.chat.id, "🎨 <b>Scegli una categoria:</b>", reply_markup=cat_keyboard())

# --- /help ---
@bot.message_handler(commands=['help'])
def cmd_help(m):
    bot.send_message(m.chat.id,
        f"<b>🎨 ValeriaFX — Guida rapida</b>\n\n"
        f"<b>Come si usa:</b>\n"
        f"1. Invia una foto\n"
        f"2. Scegli categoria e filtro\n"
        f"3. Conferma la generazione\n\n"
        f"Oppure scegli prima il filtro con /filtro, poi invia la foto.\n\n"
        f"<b>Comandi:</b>\n"
        f"/start o /reset — reimposta\n"
        f"/filtro — scegli il filtro\n"
        f"/info — versione e filtro attivo\n"
        f"/help — questa guida"
    )

# --- /info ---
@bot.message_handler(commands=['info'])
def cmd_info(m):
    uid = m.from_user.id
    fkey = user_filter[uid]
    fname = FILTERS[fkey]["label"] if fkey else "Nessuno"
    bot.send_message(m.chat.id,
        f"<b>ℹ️ ValeriaFX Info</b>\n\n"
        f"Versione: <b>{VERSION}</b>\n"
        f"Filtro attivo: <b>{fname}</b>"
    )

# --- CALLBACK POST-GENERAZIONE ---
@bot.callback_query_handler(func=lambda c: c.data in ["post_newfilter", "post_newphoto", "post_newboth"])
def handle_post(call):
    uid = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass

    if call.data == "post_newfilter":
        # Stessa foto, nuovo filtro — resetta solo il filtro
        if uid in last_img:
            pending[uid] = {'img': last_img[uid], 'filter_key': None}
        user_filter[uid] = None
        logger.info(f"🔄 {username} → nuovo filtro, stessa foto")
        bot.send_message(call.message.chat.id, "🎨 <b>Scegli il nuovo filtro:</b>", reply_markup=cat_keyboard())

    elif call.data == "post_newphoto":
        # Stesso filtro, nuova foto
        fkey = user_filter[uid]
        if not fkey:
            bot.send_message(call.message.chat.id, "⚠️ Nessun filtro attivo. Scegli un filtro prima.", reply_markup=cat_keyboard())
            return
        fname = FILTERS[fkey]["label"]
        logger.info(f"🔄 {username} → stesso filtro ({fkey}), nuova foto")
        bot.send_message(call.message.chat.id,
            f"📷 Filtro attivo: <b>{fname}</b>\n\nInvia la nuova foto da elaborare.")

    elif call.data == "post_newboth":
        # Nuova foto E nuovo filtro — reset completo
        user_filter[uid] = None
        user_category[uid] = None
        pending.pop(uid, None)
        logger.info(f"🔄 {username} → nuova foto e nuovo filtro")
        bot.send_message(call.message.chat.id,
            "🆕 <b>Ricominciamo!</b>\n\nInvia una nuova foto e scegli un nuovo filtro.",
            reply_markup=cat_keyboard())

# --- CALLBACK CATEGORIE ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_") or c.data == "back_cats")
def handle_cat(call):
    uid = call.from_user.id
    if call.data == "back_cats":
        try:
            bot.edit_message_text("🎨 <b>Scegli una categoria:</b>",
                call.message.chat.id, call.message.message_id,
                reply_markup=cat_keyboard(), parse_mode="HTML")
        except Exception:
            bot.send_message(call.message.chat.id, "🎨 <b>Scegli una categoria:</b>",
                reply_markup=cat_keyboard())
        return

    cat = call.data.replace("cat_", "")
    user_category[uid] = cat
    cat_label = CATEGORIES.get(cat, cat)
    try:
        bot.edit_message_text(f"🎨 <b>{cat_label}</b> — scegli il filtro:",
            call.message.chat.id, call.message.message_id,
            reply_markup=filter_keyboard(cat), parse_mode="HTML")
    except Exception:
        bot.send_message(call.message.chat.id, f"🎨 <b>{cat_label}</b> — scegli il filtro:",
            reply_markup=filter_keyboard(cat))

# --- CALLBACK FILTRI ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("f_"))
def handle_filter(call):
    uid = call.from_user.id
    fkey = call.data.replace("f_", "")
    if fkey not in FILTERS:
        bot.answer_callback_query(call.id, "Filtro non trovato.")
        return

    user_filter[uid] = fkey
    fname = FILTERS[fkey]["label"]
    bot.answer_callback_query(call.id, f"✅ {fname}")
    logger.info(f"🎨 {call.from_user.username or call.from_user.first_name} (id={uid}) → filtro: {fkey}")

    # Se c'è già un'immagine in attesa, prepara subito la conferma
    if uid in pending and pending[uid].get('img'):
        pending[uid]['filter_key'] = fkey
        _send_confirmation(call.message.chat.id, uid, fname)
    else:
        try:
            bot.edit_message_text(
                f"✅ Filtro selezionato: <b>{fname}</b>\n\nOra invia la foto da elaborare.",
                call.message.chat.id, call.message.message_id, parse_mode="HTML")
        except Exception:
            bot.send_message(call.message.chat.id,
                f"✅ Filtro selezionato: <b>{fname}</b>\n\nOra invia la foto da elaborare.")

# --- CALLBACK CONFERMA / ANNULLA ---
@bot.callback_query_handler(func=lambda c: c.data in ["confirm_fx", "cancel_fx"])
def handle_confirm(call):
    uid = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass

    if call.data == "cancel_fx":
        pending.pop(uid, None)
        logger.info(f"❌ {username} ha annullato.")
        bot.send_message(call.message.chat.id, "❌ <b>Annullato.</b>")
        return

    data = pending.get(uid)
    if not data or not data.get('img') or not data.get('filter_key'):
        bot.send_message(call.message.chat.id, "⚠️ Sessione scaduta. Invia di nuovo la foto.")
        return

    fkey = data['filter_key']
    fname = FILTERS[fkey]["label"]
    logger.info(f"🚀 {username} (id={uid}) → generazione | filtro: {fkey}")

    bot.send_message(call.message.chat.id,
        f"🚀 <b>Generazione avviata!</b>\n"
        f"🎨 Filtro: <b>{fname}</b>\n"
        f"⏳ Attendi ~20–35 secondi.")

    executor.submit(_run_generation, call.message.chat.id, uid, username, data)
    pending.pop(uid, None)

# --- HANDLER FOTO ---
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    uid = m.from_user.id
    username = m.from_user.username or m.from_user.first_name

    try:
        file_info = bot.get_file(m.photo[-1].file_id)
        img_data = bot.download_file(file_info.file_path)
        logger.info(f"🖼️ Foto da {username} (id={uid}), {len(img_data)} bytes")
    except Exception as e:
        logger.error(f"❌ Errore download foto da {username}: {e}")
        bot.reply_to(m, "❌ Errore nel scaricare la foto. Riprova.")
        return

    fkey = user_filter[uid]
    pending[uid] = {'img': img_data, 'filter_key': fkey}

    if not fkey:
        bot.reply_to(m, "📷 Foto ricevuta!\n\n🎨 <b>Scegli una categoria:</b>", reply_markup=cat_keyboard())
    else:
        fname = FILTERS[fkey]["label"]
        _send_confirmation(m.chat.id, uid, fname, reply_to=m.message_id)

# --- HELPER: invia conferma con preview prompt ---
def _send_confirmation(chat_id, uid, fname, reply_to=None):
    fkey = user_filter[uid]
    filter_prompt = FILTERS[fkey]["prompt"] if fkey else ""

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🚀 CONFERMA", callback_data="confirm_fx"),
        types.InlineKeyboardButton("❌ ANNULLA", callback_data="cancel_fx")
    )
    markup.add(types.InlineKeyboardButton("🔄 Cambia filtro", callback_data="back_cats"))

    # Preview prompt con chunking
    CHUNK = 3800
    header = f"🎨 Filtro: <b>{fname}</b>\n\n📝 <b>Prompt:</b>\n"
    full = filter_prompt

    if len(full) <= CHUNK:
        text = f"{header}<code>{html.escape(full)}</code>\n\nProcedere?"
        if reply_to:
            bot.send_message(chat_id, text, reply_to_message_id=reply_to, reply_markup=markup, parse_mode="HTML")
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")
    else:
        chunks = [full[i:i+CHUNK] for i in range(0, len(full), CHUNK)]
        for idx, chunk in enumerate(chunks):
            prefix = header if idx == 0 else f"<i>({idx+1}/{len(chunks)})</i>\n"
            bot.send_message(chat_id, f"{prefix}<code>{html.escape(chunk)}</code>", parse_mode="HTML",
                             **({"reply_to_message_id": reply_to} if reply_to and idx == 0 else {}))
        bot.send_message(chat_id,
            f"📋 Prompt completo ({len(chunks)} parti). Procedere?",
            reply_markup=markup, parse_mode="HTML")

# --- GENERAZIONE ---
def _run_generation(chat_id, uid, username, data):
    fkey = data['filter_key']
    filter_prompt = FILTERS[fkey]["prompt"]
    img_bytes = data['img']
    fname = FILTERS[fkey]["label"]

    t_start = time.time()
    logger.info(f"   🎨 Inizio generazione | {username} | filtro: {fkey}")

    # Wrapper editoriale per ridurre falsi positivi IMAGE_SAFETY
    EDITORIAL_WRAPPER = (
        "This is a professional editorial post-production request for a high-fashion photography project. "
        "Apply the following artistic filter to the provided image, maintaining the subject's identity, "
        "pose and composition. This is a legitimate creative and commercial photography workflow. "
        "Filter to apply: "
    )

    try:
        img_part = genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
        full_prompt = EDITORIAL_WRAPPER + filter_prompt
        contents = [full_prompt, img_part]

        use_master = FILTERS[fkey].get("use_master", True)
        if use_master and MASTER_PART:
            contents.append(MASTER_PART)
            logger.info("   ✅ MASTER_PART incluso nella generazione")
        elif use_master and not MASTER_PART:
            logger.warning("   ⚠️ MASTER_PART non disponibile — generazione senza face reference")
        else:
            logger.info(f"   ℹ️ MASTER_PART escluso per filtro {fkey} (use_master=False)")

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=genai_types.ImageConfig(image_size="2K"),
                safety_settings=[{"category": c, "threshold": "BLOCK_NONE"} for c in
                                  ["HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_HATE_SPEECH",
                                   "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            )
        )

        elapsed = round(time.time() - t_start, 1)

        if not response.candidates:
            logger.warning(f"   ⚠️ Nessun candidato per {username}")
            bot.send_message(chat_id, "❌ L'API non ha restituito risultati. Riprova.")
            return

        candidate = response.candidates[0]
        if candidate.finish_reason != "STOP":
            logger.warning(f"   ⚠️ Bloccato: {candidate.finish_reason}")
            bot.send_message(chat_id,
                f"🛡️ Generazione bloccata.\nMotivo: <b>{candidate.finish_reason}</b>")
            return

        for part in candidate.content.parts:
            if part.inline_data:
                # Salva immagine per riuso
                last_img[uid] = img_bytes

                # Bottoni post-generazione
                post_markup = types.InlineKeyboardMarkup()
                post_markup.row(
                    types.InlineKeyboardButton("🎨 Nuovo filtro, stessa foto", callback_data="post_newfilter"),
                    types.InlineKeyboardButton("🔁 Stesso filtro, nuova foto", callback_data="post_newphoto")
                )
                post_markup.row(
                    types.InlineKeyboardButton("🆕 Nuova foto e nuovo filtro", callback_data="post_newboth")
                )

                bot.send_document(
                    chat_id,
                    io.BytesIO(part.inline_data.data),
                    visible_file_name=f"fx_{fkey}.jpg",
                    caption=f"✅ {fname} — {elapsed}s"
                )
                bot.send_message(chat_id,
                    "Cosa vuoi fare adesso?",
                    reply_markup=post_markup)
                logger.info(f"   ✅ Inviato a {username} in {elapsed}s")
                return

        bot.send_message(chat_id, "❌ Nessuna immagine nella risposta. Riprova.")

    except Exception as e:
        elapsed = round(time.time() - t_start, 1)
        logger.error(f"   ❌ Crash generazione ({elapsed}s): {e}", exc_info=True)
        bot.send_message(chat_id, f"❌ Errore interno:\n<code>{html.escape(str(e))}</code>")

# --- SERVER ---
app = flask.Flask(__name__)

@app.route('/')
def health():
    return f"ValeriaFX v{VERSION} Online"

if __name__ == "__main__":
    logger.info(f"🟢 Avvio ValeriaFX Bot v{VERSION}")
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))),
        daemon=True
    ).start()
    bot.infinity_polling()
