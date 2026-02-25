# 👠 ValeriaClosetBot

Bot Telegram per il digital outfit try-on di **Valeria Cross** — genera immagini AI del personaggio che indossa qualsiasi capo di abbigliamento, partendo da una foto di riferimento.

---

## Versione attuale
`4.9.5 (Freepose)`

---

## Cosa fa

Il bot riceve una foto di un outfit (indossato su modello, su manichino, flat lay, ecc.) e genera una nuova immagine di Valeria Cross che indossa quel capo, in una posa e con un'espressione completamente nuove rispetto al riferimento.

Il soggetto generato è sempre **Valeria Cross**: personaggio transmaschile italiano, 60 anni, con caratteristiche fisiche fisse definite nel blocco identità (vedi sotto).

---

## Stack tecnico

| Componente | Dettaglio |
|---|---|
| Linguaggio | Python 3.x |
| Framework bot | pyTelegramBotAPI (`telebot`) |
| AI generativa | Google Gemini API (`nano-banana-pro-preview`) |
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
master_face.png   — Immagine di riferimento del volto di Valeria Cross
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
2. Il bot mostra il **prompt completo** che verrà inviato all'API
3. Premi **CONFERMA** per generare o **ANNULLA** per interrompere
4. Il bot invia l'immagine generata come documento `.jpg`

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

---

## Funzionalità chiave

### Traduzione automatica
Qualsiasi lingua in input viene tradotta in inglese prima della costruzione del prompt, tramite chiamata a `gemini-2.0-flash`. Se la traduzione fallisce, viene usato il testo originale.

### Freepose (v4.9.5)
Il bot non copia la posa del riferimento — genera sempre una posa editoriale nuova. Questo riduce l'effetto "faceswap" e produce immagini più naturali e integrate.

### Preview prompt con chunking
Il prompt completo viene mostrato prima della conferma. Se supera i 3800 caratteri viene spezzato in più messaggi numerati, con i pulsanti di conferma sull'ultimo messaggio.

### Reply-to-modify (v4.9.1+)
Ogni immagine generata viene salvata in memoria con il suo `message_id`. Rispondendo a quell'immagine si può richiedere una variante, che usa l'immagine generata come nuovo riferimento visivo.

### Thread sicuri
Tutte le generazioni girano in thread separati tramite `ThreadPoolExecutor` — il bot rimane reattivo anche durante generazioni lunghe (20–35s per immagine).

---

## Logging

Il bot logga su stdout con timestamp:

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

- **Una sola istanza attiva alla volta** — due istanze in polling causano errore 409 (Conflict). In caso di redeploy su Koyeb, assicurarsi che la vecchia istanza sia terminata prima che la nuova parta.
- **master_face.png** deve essere nella root del progetto, non in sottocartelle.
- Il bot usa `uid` (user ID) e non `cid` (chat ID) per lo stato per-utente — corretto per uso in chat privata.
- Le immagini generate vengono salvate in memoria (`generated_images`) solo per la sessione corrente — si perdono al riavvio del bot.

---

## Cronologia versioni

| Versione | Novità |
|---|---|
| 4.9.0 | Error handling, logging dettagliato, fix uid/cid, messaggi UX |
| 4.9.1 | Reply-to-modify: rispondi a un'immagine generata per modificarla |
| 4.9.2 | Preview del prompt completo prima della conferma |
| 4.9.3 | Chunking automatico prompt lunghi, tentativo LANGUAGE RULE |
| 4.9.4 | Traduzione automatica in inglese via API (sostituisce LANGUAGE RULE) |
| 4.9.5 | Freepose: posa ed espressione sempre nuove, gestione manichino/flat lay |
