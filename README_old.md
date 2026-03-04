# 👗 ValeriaClosetBot + 🎨 ValeriaFX — README

---

## Indice

- [ValeriaClosetBot](#-valeriaclosetbot)
- [ValeriaFX](#-valeriafx)

---

# 👗 ValeriaClosetBot

Bot Telegram per il digital outfit try-on di **Valeria Cross** — genera immagini AI del personaggio che indossa qualsiasi capo di abbigliamento, partendo da una foto di riferimento.

---

## Versione attuale
`5.0.1`

---

## Cosa fa

Il bot riceve una foto di un outfit (indossato su modello, su manichino, flat lay, ecc.) e genera una nuova immagine di Valeria Cross che indossa quel capo in 2K, con una posa e un'espressione completamente nuove rispetto al riferimento.

Il soggetto generato è sempre **Valeria Cross**: personaggio transmaschile italiano, 60 anni, con caratteristiche fisiche fisse definite nei blocchi identità (vedi sotto).

---

## Stack tecnico

| Componente | Dettaglio |
|---|---|
| Linguaggio | Python 3.x |
| Framework bot | pyTelegramBotAPI (`telebot`) |
| AI generazione immagini | Google Gemini API (`gemini-3-pro-image-preview`) |
| AI traduzione | Google Gemini API (`gemini-3-flash-preview`) |
| Web server | Flask (per health check su Koyeb) |
| Deployment | Koyeb |
| Threading | `ThreadPoolExecutor` (max 4 worker) |

---

## Variabili d'ambiente richieste

```
TELEGRAM_TOKEN_CLOSET   — Token del bot Telegram
GOOGLE_API_KEY          — Chiave API Google Gemini
```

---

## File richiesti nella root del progetto

```
master_face.png   — Immagine di riferimento del volto di Valeria Cross.
                    Viene passata all'API come REFERENCE 1 ad ogni generazione.
                    Se non trovata, il bot funziona lo stesso ma senza riferimento volto.
```

---

## Comandi disponibili

| Comando | Funzione |
|---|---|
| `/start` o `/reset` | Reimposta le preferenze utente (formato 2:3, quantità 1) |
| `/formato` | Scegli il formato dell'immagine output |
| `/settings` | Scegli la quantità di foto da generare (1–4) |
| `/help` | Guida rapida |
| `/info` | Versione, stato master face, impostazioni attuali |

---

## Formati disponibili

`2:3` `3:4` `4:5` `9:16` `2:1` `3:2` `4:3` `5:4` `16:9` `3:1`

Default: `2:3`

---

## Come si usa

### Flusso base
1. Invia una **foto dell'outfit** (con didascalia opzionale per istruzioni di scena)
2. Il bot mostra il **prompt completo** (blocchi B1–B4) che verrà inviato all'API
3. Premi **CONFERMA** per generare o **ANNULLA** per interrompere
4. Il bot invia l'immagine generata in **risoluzione 2K** come documento `.jpg`

### Solo testo (senza foto outfit)
Invia solo un testo descrittivo — il bot genera senza riferimento visivo outfit.

### Reply per modifica
Rispondi a un'immagine già generata con un'istruzione di modifica (es. "Cambia lo sfondo con una spiaggia tropicale"). Il bot usa l'immagine generata come nuovo riferimento e applica la modifica richiesta.

---

## Struttura del prompt

Il prompt inviato all'API è composto da 4 blocchi fissi + la scena utente:

```
BLOCK 1  →  Definisce il ruolo dei riferimenti immagine
             (REFERENCE 1 = master_face, REFERENCE 2 = outfit)

BLOCK 2  →  Identità Valeria Cross
             (transmasculine, 60yo, corpo femminile, barba argento, occhiali Vogue)

BLOCK 3  →  Istruzioni d'azione
             - Mantieni l'outfit esatto dal riferimento
             - Genera posa ed espressione NUOVE (non copiare il riferimento)
             - Se il riferimento è un manichino/flat lay, inventa una posa naturale
             - Usa il riferimento solo per outfit, ambiente e luce

BLOCK 4  →  Impostazioni tecniche
             (8K, cinematic, 85mm, watermark "feat. Valeria Cross 👠")

NEGATIVE →  Prompt negativi
             (female face, body hair, masculine body shape, flat chest)
```

Il testo utente viene inserito come `SCENE/DESTINATION` tra B3 e B4.
La preview mostra tutti i blocchi (B1–B4) prima della conferma.

---

## Funzionalità chiave

### Traduzione automatica
Solo l'input reale dell'utente viene tradotto in inglese tramite `gemini-3-flash-preview`. Il testo default ("Maintain the exact scene from the reference.") non viene tradotto. Se la traduzione fallisce, viene usato il testo originale.

### Risoluzione 2K
Ogni generazione usa `image_config=genai_types.ImageConfig(image_size="2K")` — upgrade rispetto al default 1K.

### Preview prompt completo con chunking
Il prompt completo (tutti i blocchi B1–B4) viene mostrato prima della conferma. Se supera i 3800 caratteri viene spezzato in più messaggi numerati, con i pulsanti di conferma sull'ultimo messaggio.

### Reply-to-modify
Ogni immagine generata viene salvata in memoria con il suo `message_id`. Rispondendo a quell'immagine si può richiedere una variante, che usa l'immagine generata come nuovo riferimento visivo.

### Thread sicuri
Tutte le generazioni girano in thread separati tramite `ThreadPoolExecutor` — il bot rimane reattivo anche durante generazioni lunghe (20–35s per immagine).

---

## Logging

```
🟢  Avvio bot
🔄  /start e reset
✏️  Input utente ricevuto
🌐  Traduzione testo
🎨  Inizio scatto
✅  Scatto inviato (con tempo di generazione)
❌  Errori generazione o invio
⚠️  Warning (master face mancante, traduzione fallita, ecc.)
```

---

## Note operative

- **Una sola istanza attiva alla volta** — due istanze in polling causano errore 409. In caso di redeploy su Koyeb, assicurarsi che la vecchia istanza sia terminata prima che la nuova parta.
- **master_face.png** deve essere nella root del progetto, non in sottocartelle.
- Il bot usa `uid` (user ID) e non `cid` (chat ID) per lo stato per-utente.
- Le immagini generate vengono salvate in memoria (`generated_images`) solo per la sessione corrente — si perdono al riavvio del bot.
- Blocchi comuni: `IMAGE_OTHER` (falso positivo, cambiare immagine), `IMAGE_SAFETY` (combinazione outfit/scena borderline, riprovare).

---

## Cronologia versioni

| Versione | Novità |
|---|---|
| 4.9.0 | Error handling, logging dettagliato, fix uid/cid |
| 4.9.1 | Reply-to-modify: rispondi a un'immagine generata per modificarla |
| 4.9.2 | Preview del prompt completo prima della conferma |
| 4.9.3 | Chunking automatico prompt lunghi |
| 4.9.4 | Traduzione automatica in inglese via API |
| 4.9.5 | Freepose: posa ed espressione sempre nuove |
| 5.0.0 | Migrazione a `gemini-3-pro-image-preview`, preview mostra tutti i blocchi B1–B4, traduzione solo su input reale utente |
| 5.0.1 | Risoluzione 2K (`image_size="2K"`), health check aggiornato |

---
---

# 🎨 ValeriaFX

Bot Telegram per l'applicazione di filtri di post-produzione artistica a foto caricate dall'utente. Lavora su qualsiasi foto — non richiede necessariamente il soggetto Valeria Cross.

## Versione attuale
`2.0.5`

---

## Cosa fa

Riceve una foto dall'utente, mostra un menu di categorie e filtri, e genera una nuova immagine con il filtro selezionato applicato in 2K. Supporta 21 filtri divisi in 5 categorie. Dopo ogni generazione offre bottoni per continuare con la stessa foto, lo stesso filtro, o ricominciare da zero.

---

## Stack tecnico

| Componente | Dettaglio |
|---|---|
| Linguaggio | Python 3.x |
| Framework bot | pyTelegramBotAPI (`telebot`) |
| AI generazione immagini | Google Gemini API (`gemini-3-pro-image-preview`) |
| Web server | Flask (per health check su Koyeb) |
| Deployment | Koyeb |
| Threading | `ThreadPoolExecutor` (max 4 worker) |

---

## Variabili d'ambiente richieste

```
TELEGRAM_TOKEN_FX   — Token del bot Telegram
GOOGLE_API_KEY      — Chiave API Google Gemini
```

---

## File richiesti nella root del progetto

```
master_face.png   — Immagine di riferimento del volto di Valeria Cross.
                    Inclusa nella generazione per i filtri Bikini Scenes.
                    Se non trovata, il bot funziona lo stesso (con volto generico).
```

---

## Comandi disponibili

| Comando | Funzione |
|---|---|
| `/start` o `/reset` | Reimposta stato utente |
| `/filtro` o `/filter` | Scegli il filtro prima di inviare la foto |
| `/info` | Versione e filtro attivo |
| `/help` | Guida rapida |

---

## Come si usa

### Flusso standard
1. Invia una **foto**
2. Scegli la **categoria** dal menu
3. Scegli il **filtro**
4. Il bot mostra il **prompt del filtro** con i pulsanti CONFERMA / ANNULLA
5. Alla conferma genera l'immagine in **2K** e la invia come documento `.jpg`
6. Scegli tra i bottoni post-generazione

### Flusso alternativo (filtro prima)
1. `/filtro` → scegli categoria e filtro
2. Invia la foto → il bot va direttamente alla conferma

---

## Filtri disponibili (21 totali)

### 🎨 Stilistici
| Chiave | Label |
|---|---|
| `cinematic_highangle` | ⬆️⬇️ Cinematic High-Angle |
| `dramatic` | ⬆️ Dramatic Low-Angle |
| `glossy` | 🌟 Glossy Opal |
| `iridescent` | 🌈 Iridescent |
| `rainbow_neon` | 🌈🌈 Rainbow Neon |
| `galaxy` | 🌌 Galaxy Couture |
| `neon_hdr` | 💛 Neon HDR |

### ✨ Fantasy & Art
| Chiave | Label |
|---|---|
| `stained_glass` | 🎐 Stained Glass |
| `underwater` | 🧜 Underwater Gold |
| `3d_synthetic` | 🪟 3D Synthetic |
| `graffiti` | 🧯 Graffiti Artist |

### 🏙️ Scenografici
| Chiave | Label |
|---|---|
| `giantess` | 🏙️ Giantess NYC |
| `action_figure` | 🪆 Action Figure |
| `art_doll` | 👯 Art Doll Exhibition |
| `toy_window` | 🎎 Toy Store Window |

### 🔄 Varianti
| Chiave | Label |
|---|---|
| `new_pose` | 🆕 New Pose |
| `triple_set` | 3️⃣× Triple Set |
| `triptych` | 3️⃣❌1️⃣ Triptych GHI |

### 👙 Bikini Scenes
| Chiave | Label |
|---|---|
| `bikini_night` | 🌙 Night Lingerie |
| `bikini_bed` | 👙🛌 Bed Editorial |
| `bikini_selfie` | 👙🤳 Beach Selfie |
| `bikini_selfie2` | 👙🤳2 Beach Selfie v2 |
| `bikini_club` | 👙🐶 Beach Club |

---

## Funzionalità chiave

### MASTER_PART incluso
`master_face.png` viene caricato all'avvio e incluso in ogni chiamata API. Fondamentale per i filtri Bikini Scenes che ricostruiscono il soggetto Valeria Cross. Per i filtri stilistici puri non altera il comportamento.

### Editorial wrapper
Ogni prompt viene preceduto da un wrapper editoriale che contestualizza la richiesta come post-produzione fotografica professionale, riducendo i falsi positivi `IMAGE_SAFETY`.

### Preview prompt
Prima della conferma viene mostrato il prompt del filtro completo (con chunking automatico a 3800 chars se necessario).

### Bottoni post-generazione
Dopo ogni immagine generata appaiono tre bottoni:
- **🎨 Nuovo filtro, stessa foto** — mantiene la foto, resetta il filtro
- **🔁 Stesso filtro, nuova foto** — mantiene il filtro, attende una nuova foto
- **🆕 Nuova foto e nuovo filtro** — reset completo, mostra menu categorie

### Salvataggio ultima immagine
`last_img[uid]` salva l'ultima foto usata per il riuso con "Nuovo filtro, stessa foto".

---

## Note su IMAGE_SAFETY

Il filtro `IMAGE_SAFETY` è gestito lato Google e può scattare su alcune combinazioni foto+filtro indipendentemente dai safety settings impostati. Non è eliminabile al 100%. Soluzioni:
- Riprovare (il modello ha variabilità naturale)
- Cambiare foto
- La presenza di `master_face.png` (foto reale) può aumentare la sensibilità su filtri Bikini Scenes

---

## Logging

```
🟢  Avvio bot
✅  master_face.png caricata
🔄  /start e reset
🎨  Selezione filtro
🖼️  Foto ricevuta
🚀  Generazione avviata
🎨  Inizio generazione (con filtro)
✅  MASTER_PART incluso
✅  Immagine inviata (con tempo)
❌  Errori
⚠️  Warning
```

---

## Note operative

- **Una sola istanza attiva** — due istanze causano errore 409.
- Il bot usa `uid` per lo stato per-utente.
- Lo stato filtro (`user_filter`) persiste tra le foto nella stessa sessione.
- Al riavvio del bot tutti gli stati in memoria vengono persi.

---

## Cronologia versioni

| Versione | Novità |
|---|---|
| 1.0.0 | Base funzionante, menu categorie e filtri |
| 1.0.1 | Preview prompt con chunking automatico |
| 2.0.0 | Bottoni post-generazione (nuovo filtro / nuova foto), `last_img` per riuso |
| 2.0.1 | Risoluzione 2K, editorial wrapper anti-IMAGE_SAFETY |
| 2.0.2 | Terzo bottone post-generazione: "Nuova foto e nuovo filtro" |
| 2.0.3 | Aggiunto MASTER_PART alla generazione (fix: era definito ma non usato) |
| 2.0.4 | Fix critico: `get_face_part()` e `MASTER_PART` non erano definiti nel file FX |
| 2.0.5 | Nuovo filtro: ⬆️⬇️ Cinematic High-Angle (categoria Stilistici, prima posizione) |
