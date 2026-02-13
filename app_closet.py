import os
import google.generativeai as genai
from flask import Flask, request, jsonify

# ==========================================
# CONFIGURAZIONE IDENTITÀ VALERIA CROSS
# ==========================================
# [cite: 2026-02-08, 2025-12-01, 2025-11-21, 2025-11-10]

VALERIA_FACE = (
    "Male Italian face, ~60 years old. Oval-rectangular. Ultra-detailed skin (pores, wrinkles, bags). "
    "Expression: calm, half-smile, NO teeth. Eyes dark brown/green. Beard: light grey/silver, groomed, 6-7 cm. "
    "Glasses MANDATORY: thin octagonal Vogue, Havana dark (NEVER removed)."
)

VALERIA_BODY = (
    "SUBJECT: Nameless Italian transmasculine avatar. Body: soft feminine, harmonious hourglass, "
    "prosperous full breasts (cup D), 180cm, 85kg. Posture grounded. "
    "Body completely hairless (arms, legs, chest, breasts - hair NO!)."
)

VALERIA_HAIR = (
    "HAIR: Light grey/silver. Short elegant Italian style, volume. Sides 1-2 cm, nape exposed. Top <15 cm. "
    "Hair NEVER touching neck, shoulders, or clavicles."
)

# ==========================================
# VOGUE SHIELD: LOGICA DI SANITIZZAZIONE
# ==========================================
# [cite: 2026-02-08]

def vogue_shield(text):
    """Sostituisce i termini trigger con lessico editoriale Vogue."""
    dictionary = {
        "lingerie": "high-fashion editorial loungewear",
        "bikini": "couture swimwear study",
        "underwear": "technical base layer garment",
        "briefs": "tailored editorial bottoms",
        "panty": "minimalist high-fashion co-ord",
        "bra": "sculpted cropped bodice",
        "sexy": "avant-garde architectural",
        "naked": "skin-tone textile focus",
        "thong": "geometric structural bottom"
    }
    sanitized = text.lower()
    for trigger, safe in dictionary.items():
        sanitized = sanitized.replace(trigger, safe)
    return sanitized

# ==========================================
# INIZIALIZZAZIONE MODELLI GEMINI
# ==========================================

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Modelli Gemini 3 [cite: 2026-02-08]
analyzer = genai.GenerativeModel('gemini-3-flash-preview')
generator = genai.GenerativeModel('gemini-3-pro-image-preview')

app = Flask(__name__)

@app.route('/', methods=['GET'])
def health_check():
    return "Valeria Closet Bot V2.7.1 - Status: OPERATIONAL on Port 10000", 200

@app.route('/generate', methods=['POST'])
def process_request():
    try:
        data = request.json
        image_url = data.get("image_url")

        # 1. ANALISI VISIVA (Visual Analyzer)
        # [cite: 2026-02-08]
        analysis_prompt = (
            "Analyze this outfit for a Vogue editorial. Describe fabrics, cuts, "
            "and patterns with technical precision. Focus on the garment construction."
        )
        analysis_response = analyzer.generate_content([analysis_prompt, image_url])
        raw_description = analysis_response.text

        # 2. SANITIZZAZIONE (Vogue Shield)
        # [cite: 2026-02-08]
        safe_outfit = vogue_shield(raw_description)

        # 3. COSTRUZIONE MASTER PROMPT (Generator)
        # [cite: 2026-02-08, 2026-01-28, 2025-11-23, 2026-02-04]
        master_prompt = (
            f"IMAGE CONCEPT: High-fashion Vogue cover, 8K, cinematic realism. \n"
            f"IDENTITY & FACE: {VALERIA_FACE} \n"
            f"BODY & STRUCTURE: {VALERIA_BODY} \n"
            f"HAIR: {VALERIA_HAIR} \n"
            f"OUTFIT: {safe_outfit} \n"
            f"CAMERA: 85mm, f/2.8, ISO 200, 1/160s. Focus on face/torso. Shallow depth of field, natural bokeh. \n"
            f"RENDERING: Subsurface Scattering, Global Illumination, Fresnel, Frequency separation on skin. \n"
            f"WATERMARK: 'feat. Valeria Cross 👠' (elegant cursive, champagne, bottom center/left, opacity 90%). \n"
            f"NEGATIVE PROMPT: female face, young, smooth skin, distortion, long hair, ponytail, bun, braid, "
            f"hair touching neck/shoulders, body hair, chest hair, leg hair, 1:1 format."
        )

        # 4. DOUBLE SHOT (Generazione Parallela)
        # [cite: 2026-02-08, 2025-11-23]
        results = []
        for i in range(2):
            try:
                # Aspect Ratio forzato per evitare l'1:1 [cite: 2025-11-23]
                image_output = generator.generate_content(
                    master_prompt,
                    generation_config={"aspect_ratio": "3:4"}
                )
                results.append(image_output.url)
            except Exception as e:
                results.append(f"Shot {i+1} Blocked: {str(e)}")

        return jsonify({
            "status": "success",
            "outfit_analysis": safe_outfit,
            "images": results
        })

    except Exception as global_err:
        return jsonify({"status": "error", "message": str(global_err)}), 400

if __name__ == '__main__':
    # Configurazione per Render (Port 10000) [cite: 2026-02-08]
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    
