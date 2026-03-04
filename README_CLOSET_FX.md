# 👗 ClosetBot & 🎨 ValeriaFX — README

> Aggiornato: Marzo 2026

---

## 👗 ClosetBot v5.1.2

### Cosa fa
Riceve una foto di un outfit (reale o di riferimento) e genera nuovi scatti fotografici di Valeria Cross indossando quell'outfit, in pose e ambienti diversi.

### Modalità
- **Foto outfit** → descrive automaticamente l'outfit via Vision e genera il prompt
- **Testo libero** → descrizione manuale dell'outfit da generare
- **Reply a uno scatto** → modifica/rigenera partendo dall'immagine ricevuta (architect mode)

### Comandi
| Comando | Funzione |
|---|---|
| `/start` | Avvia il bot |
| `/formato` | Sceglie il formato (2:3, 1:1, 16:9…) |
| `/settings` | Imposta numero di scatti (1–4) |
| `/help` | Guida rapida |
| `/info` | Versione e stato master face |

### Note tecniche
- Master face caricata da `MASTER_FACE_URL` (env var)
- Motore: `gemini-3-pro-image-preview`
- Safety settings: BLOCK_NONE su tutte le categorie
- Watermark automatico: `feat. Valeria Cross 👠`
- Keep-alive: cron-job esterno (Flask presente ma non necessario)

---

## 🎨 ValeriaFX v3.0.6

### Cosa fa
Applica filtri creativi e collage a qualsiasi foto inviata. Funziona con foto di Valeria o di chiunque altro (filtri universali).

### Struttura menu
```
🏠 Homepage
├── ✨ New Pose          → genera una nuova posa dallo stesso look
├── 🎭 Stili            → 4 filtri stile (3D, Anime, Oil Painting, Sketch)
├── 🌍 Ambientazioni    → 4 filtri location (Beach, City, Forest, Studio)
├── 💫 Effetti          → 5 filtri effetto (Gold, Neon, Vintage, Glam, B&W)
└── 🖼️ Collage
    ├── Triple Set       → 3 pose stesso outfit
    ├── Triptych GHI     → 3 versioni colore (Gold/Holographic/Iridescent)
    ├── 🌸 Pastel Clones → 7 cloni fashion magazine spread
    ├── 🟦 Collage 2×2   → 4 angoli camera
    ├── 📷 Photobooth 4×4 → 16 espressioni volto
    ├── 🧍 Full Body 3×3 → 9 pose full body (randomizzate)
    └── 🐾 Pet Mosaic 4×4 → 16 espressioni animale
```

### Filtri universali (use_master: False)
Tutti i filtri Collage usano la **foto inviata** come identità — funzionano con qualsiasi soggetto, non solo Valeria.

### Full Body 3×3 — randomizzazione
Pool di 15 pose disponibili. Ad ogni generazione ne vengono pescate 9 in ordine casuale → oltre 1.8 miliardi di combinazioni possibili.

### Note tecniche
- Motore: `gemini-3-pro-image-preview`
- Master face: caricata da `MASTER_FACE_URL` (usata solo dai filtri con `use_master: True`)
- Safety settings: BLOCK_NONE su tutte le categorie
- Keep-alive: cron-job esterno (Flask presente ma non necessario)
- `resolve_prompt(fkey)` gestisce prompt statici e callable (lambda)
