# README — Ecosistema Bot Valeria Cross
**Aggiornato:** 13 Marzo 2026

---

## ECOSISTEMA BOT

```
ARCHITECT (A) = 🖼️/T → Prompt ottimizzato (T2T)
VOGUE (B)     = T/Prompt + A → {Immagine generata} (T2I)
FX (D)        = {Immagine generata} + Filtro → {Immagine filtrata} (I2I)
CABINA (C)    = 🖼️ costume + Filtro → {Valeria in costume} (pipeline neutra)
SORPRESA (E)  = 🎲 Random 14 variabili → {Immagine generata} (T2I)
```

---

## VERSIONI DEPLOYATE

| Bot | Versione | File | Note |
|-----|----------|------|------|
| SorpresaBot | 1.1.4 | `sorpresa-114.py` | ✅ |
| CabinaBot | 1.6.8 | `cabina-168.py` | ✅ |
| ValeriaFX | 3.6.7 | `valeriafx-367.py` | ✅ |
| VogueBot | 5.12.9 | `vogue-5129.py` | ✅ |
| ArchitectBot | 7.11.5 | `architect-7115.py` | ✅ (7116 non funzionante) |

**Token env:** `TELEGRAM_TOKEN_SORPRESA`, `TELEGRAM_TOKEN_CLOSET`, `TELEGRAM_TOKEN_FX`, `TELEGRAM_TOKEN_VOGUE`, `TELEGRAM_TOKEN_ARCHITECT`

**Deploy:** tutti su Koyeb — Flask health check obbligatorio su porta 10000

---

## IDENTITÀ VALERIA CROSS

- 60 anni, uomo italiano, viso ovale-rettangolare
- Occhiali Vogue Havana tartaruga scura ottagonali (SEMPRE presenti)
- Barba argento 6-7cm, capelli corti argento
- Corpo femminile: 180cm, 85kg, seno D-cup, hourglass
- Pelle liscia (zero peli su tutto il corpo)
- Watermark: `feat. Valeria Cross 👠` — corsivo champagne, piccolo, bottom center
- Tutti i bot usano `masterface.png` (non `master_face.png`)
- Architect non usa master face (genera solo prompt testuali)

---

## REGOLE OPERATIVE

- Ogni modifica = bump versione; file precedente resta vivo (non sovrascrivere)
- NON applicare modifiche senza esplicito ok di Walter ("Vai" = ok)
- File di lavoro: `/home/claude/` — Output finali: `/mnt/user-data/outputs/`
- Quota Gemini: 50 immagini/giorno (piano gratuito)
- Versione nel filename E versione dentro il file devono essere aggiornate insieme
- 409 Conflict = due istanze in parallelo → restart manuale sul deploy nuovo

---

## SORPRESA BOT v1.1.4

### Variabili (14 — filtro_fx rimosso dalle opzioni)
| Var | Emoji | Note |
|-----|-------|------|
| sfondo | 🏛️ | 25 opzioni + 2 nuovi (café parigino, townhouse georgiana) |
| cielo | 🌤️ | 15 opzioni |
| posa | 🧍 | 20 opzioni |
| espressione | 😏 | 15 opzioni |
| outfit_top | 👚 | 16 opzioni |
| outfit_bottom | 👗 | 16 opzioni |
| scarpe | 👠 | 15 opzioni |
| colore | 🎨 | 15 opzioni |
| accessori | 💍 | 15 opzioni |
| stile | ✨ | 17 opzioni |
| luce | 💡 | 16 opzioni |
| punto_di_ripresa | 📷 | 15 opzioni |
| pattern | 🔵 | 18 opzioni |
| filtro_fx | ✨ | solo `none` — filtri rimossi in v1.1.4 |
| stile_artistico | 🎨 | 12 opzioni |

### Assi di compatibilità (10)
- Asse 1–8: mutua esclusione stili, sfondi, luci, ecc.
- Asse 9: formato smart — `get_formato()` calcola aspect ratio ottimale (2:3, 9:16, 3:4, 4:5, 16:9, 3:2, 21:9, auto)
- Asse 10: FX con sfondo proprio (Galaxy Couture, Cloud Sculpture, Action Figure, Art Doll, Stained Glass) → sostituisce sfondo terrestre con `white seamless studio`

### Formato API (21:9 rimane riservato a FX Stereo in ValeriaFX)
Auto, 1:1, 9:16, 16:9, 3:4, 4:3, 3:2, 5:4, 4:5, 21:9, 4:1, 1:4, 8:1, 1:8

### Flow
1. `/start` → 🎲 Tira i dadi!
2. Mostra combo estratta → ✅ Conferma / 🎲 Ritira
3. Conferma → ⏳ Generazione in corso...
4. Immagine → Prompt generico (msg 1) → Caption Threads (msg 2) → pulsanti

### Comandi
- `/start` / `/reset` — avvio e reset
- `/lastprompt` — mostra ultimo prompt inviato all'API

---

## VOGUE BOT v5.12.9

### Flow
1. Utente invia testo/prompt → traduzione EN → ottimizzazione → conferma
2. 3 bypass: ARCH_TAG (prompt Architect), CLOSET_TAG (prompt Cabina), faceswap editoriale
3. Generazione → immagine + caption
4. `/lastprompt` — recupera ultimo prompt (utile per faceswap)

### Fix v5.12.9
- `finish_reason` normalizzato a stringa pulita (fix crash su `MALFORMED_FUNCTION_CALL`)
- `send_message` wrappato in try/except nei thread di generazione — il pulsante Riprova arriva sempre

### Comandi
- `/lastprompt` — mostra ultimo prompt inviato all'API
- `/help`, `/info`, `/settings`

---

## VALERIAFX v3.6.7

### Filtri disponibili per categoria

**PROSPETTIVA**
- ⬆️⬇️ Cinematic High-Angle
- ⬆️ Dramatic Low-Angle

**STYLISTIC**
- 🌟 Glossy Opal
- 🌈 Iridescent
- 🌌 Galaxy Couture
- 👻 Ghost Temporal
- 💧 Dissolvence

**FANTASY & ART**
- 🎐 Stained Glass
- 🪟 3D Synthetic
- 🧯 Graffiti Artist
- ☁️ Cloud Sculpture
- 🪆 Action Figure
- 👯 Art Doll Exhibition

*(Rainbow Neon e Neon HDR rimossi in v3.6.7)*

### Modalità speciali
- **🆕 New Pose** — nuova generazione senza filtro
- **🎥 3D Stereo** — converte qualsiasi immagine in stereoscopico cross-eyed (21:9, due pannelli affiancati)
- **🖼️ Mosaic** — collage 2×2 o 3×3 da 4 o 9 foto (`/mosaic`, `/done`)

### Flow standard
1. Scegli categoria → scegli filtro
2. Invia foto → conferma → generazione
3. Immagine → caption + link `https://t.me/valeriacross_gallery`
4. Pulsanti: Riprova / Stesso filtro nuova foto / Nuova foto e filtro

### Comandi
- `/start` / `/reset`, `/filtro`, `/help`, `/info`
- `/lastprompt` — mostra ultimo prompt inviato all'API
- `/mosaic`, `/done`

---

## CABINA BOT v1.6.8

### Flow
1. `/start` → scegli filtro → scegli formato e numero foto
2. Invia foto outfit di riferimento
3. Analisi outfit neutra (Flash) → `build_full_prompt` → conferma
4. Generazione → immagine

### Comandi
- `/start`, `/reset`, `/formato`, `/settings`, `/info`, `/help`
- `/lastprompt` — mostra ultimo prompt inviato all'API

---

## ARCHITECT BOT v7.11.5

### Engine profiles
ChatGPT, Gemini, Grok, Qwen, Meta

### Bug noto
`hard_cap_prompt` definita dopo `bot.infinity_polling` → `NameError` negli handler.
Fix pronto come `architect-7116.py` — non deployare senza ok Walter.

### Comandi
- `/help`, `/info`
- `/lastprompt` — **non ancora implementato** (prossima versione)

---

## LEZIONI APPRESE

- **Formato API:** parametro `aspect_ratio` in `ImageConfig` accetta stringhe testuali (es. `"21:9"`)
- **FX con sfondo proprio:** Galaxy Couture/Cloud Sculpture ignorano sfondo terrestre → neutralizzare con white seamless studio
- **MALFORMED_FUNCTION_CALL:** `finish_reason` è un enum nell'SDK → usare `.name` per ottenere stringa pulita
- **Sessione mosaic zombie:** selezionare un filtro ora pulisce automaticamente sessioni mosaic pendenti
- **3D Stereo:** prompt unico con due pannelli in 21:9 — Gemini capisce il parallax differenziale foreground/background
- **Masterface senza ancora testuale:** Gemini la ignora → serve frase esplicita
- **Face lock assente:** Gemini genera donna generica → VALERIA_FACE_LOCK obbligatorio
