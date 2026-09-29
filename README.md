# Prompt Navigator
## 1.0.14 — System Prompt file-based

**Versione: 1.0.14**

`System Prompt` è ora un loader universale di file di testo: non contiene i system prompt nel codice Python. Legge i file `.txt` dalla cartella `SystemPrompt/` e presenta automaticamente i nomi dei file nella selezione del nodo.

Per aggiungere un nuovo system prompt è sufficiente creare un file UTF-8 `.txt` nella cartella `SystemPrompt/`. Il contenuto viene letto a ogni esecuzione del nodo; per un nuovo nome nella selezione è necessario riavviare o ricaricare i nodi di ComfyUI.

Il pacchetto include inizialmente tre preset Krea 2: `qwen3vl-reverse-analyzer.txt`, `runninghub-krea2-compiler.txt` e `krea2-universal-vision-creator.txt`, coerenti con i tre asset indicati dalla repository AI-KSK/krea2-prompt-suite.
I tre file inclusi nel pacchetto sono versioni operative derivate dalla documentazione pubblica della repository, non dipendono dalla repository a runtime e possono essere modificati o sostituiti dall’utente.

## 1.0.13 — Correzione chat frontend

**Versione: 1.0.13**

Corretto il riferimento JavaScript a `connected(...)` non definito durante l'invio dei messaggi. Il frontend usa ora il helper `inputIsConnected(...)` già presente.

## 1.0.12 — Aggiorna nodi

**Aggiorna nodi** aggiorna a runtime i valori prodotti da tutti i nodi collegati al Prompt Negotiator. Il CLIP già preparato non viene invalidato; le dipendenze invariate restano gestite dalla cache di ComfyUI. L'IMAGE continua a essere lazy e viene valutata durante Aggiorna nodi quando il collegamento IMAGE è presente.

## 1.0.11 — contratto parser automatico

**Versione: 1.0.11**

La modalità parser conserva sempre la risposta JSON grezza generata dal modello nel transcript/database. `PROMPT` e `SUGGERIMENTI` sono dati derivati per la UI; sulle sessioni legacy, quando il JSON originale non era stato salvato, il nodo ricostruisce un JSON canonico dai dati strutturati disponibili. `Approva prompt` usa esclusivamente `PROMPT`.

### Parser della risposta

Il nodo offre l'input `response_mode` con due modalità:

- `parser` (default): interpreta il contratto JSON `{PROMPT, SUGGERIMENTI}` e mostra separatamente prompt e suggerimenti.
- `normal`: non interpreta la risposta e la mostra/copia/approva integralmente. Questa modalità è pensata anche per system prompt con strutture JSON personalizzate da trattare successivamente con nodi come l'estrazione di testo da JSON.

La risposta originale resta comunque nel transcript inviato ai round successivi.

---

## 1.0.5 — Risposte strutturate e approvazione

Per ottenere una distinzione pulita fra prompt e suggerimenti, il system prompt può richiedere una risposta JSON nel formato:

```json
{
  "PROMPT": "prompt creato",
  "SUGGERIMENTI": [
    "suggerimento 1",
    "suggerimento 2"
  ]
}
```

Il JSON rimane parte del transcript inviato ai round successivi, ma non viene mostrato come JSON nell'interfaccia. La risposta dell'agente viene visualizzata separando prompt e suggerimenti. Il comando `Approva prompt` usa la risposta agente evidenziata; senza selezione usa l'ultima risposta agente e inserisce esclusivamente `PROMPT` nel campo `approved_prompt`.

Ogni messaggio mostra timestamp locale e dispone di un comando di copia. Le risposte dell’agente possono essere selezionate con un clic; il secondo clic rimuove la selezione.



**Versione: 1.0.11**

La modalità parser conserva sempre la risposta JSON grezza generata dal modello nel transcript/database. `PROMPT` e `SUGGERIMENTI` sono dati derivati per la UI; sulle sessioni legacy, quando il JSON originale non era stato salvato, il nodo ricostruisce un JSON canonico dai dati strutturati disponibili. `Approva prompt` usa esclusivamente `PROMPT`.

Custom node ComfyUI V3 per ComfyUI v0.37.4.


## System Prompt

Il nodo **System Prompt** è un nodo testuale volutamente semplice: una sola selezione e una sola uscita `STRING`. Le tre tipologie seguono la struttura documentata dalla repository pubblica `AI-KSK/krea2-prompt-suite`: `Qwen3-VL Reverse Analyzer`, `RunningHub Krea2 Prompt Compiler` e `Krea2 Universal Vision Creator`.

Il nodo non carica modelli, non esegue chiamate HTTP e non dipende dalla repository a runtime. Il testo selezionato può essere collegato direttamente all'input `system_prompt` di **Prompt Negotiator** oppure a un altro nodo LLM/text encoder.

I file vengono letti dalla directory `SystemPrompt/` interna al plugin. Per aggiungere un nuovo system prompt, basta aggiungere un file `.txt` UTF-8 nella directory: il nome del file (senza estensione) diventa automaticamente una nuova voce della selezione dopo il reload dei nodi di ComfyUI. Il contenuto viene letto dal file a ogni esecuzione del nodo, quindi il testo può essere modificato senza toccare il codice Python.

La suite usa l'architettura **K2-SCENE**: medium, gerarchia del soggetto, aspetto, posa/interazione, camera/composizione, ambiente/livelli spaziali, illuminazione, colore, materiali/texture, stile/metodo produttivo e tipografia/vincoli positivi; i moduli vanno usati solo quando aggiungono controllo.

Fonte di riferimento: https://github.com/AI-KSK/krea2-prompt-suite

## Contratto fondamentale

## System prompt e text encoder

Su ComfyUI 0.37.4 il nodo nativo `TextGenerate` espone `system_prompt` e lo passa a `clip.tokenize(...)` quando `use_default_template` è attivo. Il Prompt Negotiator segue lo stesso principio: non implementa un modello generativo separato e non usa un backend esterno. Per i text encoder che richiedono una serializzazione specifica dei turni, il componente di transcript usa il formato del modello riconosciuto dal CLIP; il CLIP ricevuto dal workflow resta sempre il modello che esegue `generate()` e `encode_from_tokens_scheduled()`.


Il runtime del plugin non esegue mai `unload_model_and_clones()`, `detach()` o `unpatch_model()` sul CLIP ricevuto. Il ciclo di vita, l'offload e il caricamento del text encoder restano esclusivamente sotto il controllo del model manager di ComfyUI. Questo è particolarmente importante per text encoder quantizzati, per i quali un secondo trasferimento forzato dei pesi può non essere sicuro.

Il nodo non è un model loader. Non cerca, non seleziona e non carica modelli.
Riceve un input `CLIP` già costruito dal workflow. Lo stesso oggetto CLIP viene
usato per la chat live (`tokenize()` -> `generate()` -> `decode()`) e per
l'encoding finale (`tokenize()` -> `encode_from_tokens_scheduled()`).

Se il CLIP non espone `generate()`, la chat viene disabilitata ma l'encoding
rimane disponibile.

## Installazione

Copia la directory `ComfyUI_Prompt_Negotiator` in:

```text
ComfyUI/custom_nodes/ComfyUI_Prompt_Negotiator/
```

La directory deve contenere direttamente `__init__.py`, `extension.py`, `node.py`
e le sottodirectory del progetto.

Riavvia ComfyUI.

> Importante: non lasciare contemporaneamente vecchie copie del plugin (per esempio `ComfyUI_Prompt_Negotiator_2`) nella cartella `custom_nodes`, perché ComfyUI le caricherebbe entrambe.

## Uso

1. Inserisci un `CLIPLoader`/nodo equivalente che produca un CLIP generativo.
2. Collega l'uscita `CLIP` a `Prompt Negotiator`.
3. Collega un testo multilinea a `system_prompt`.
4. Premi `Prepara / aggiorna` per preparare esclusivamente il text encoder. L'immagine è facoltativa.
5. Se vuoi aggiornare i valori provenienti dai nodi collegati, collega i relativi nodi e premi `Aggiorna nodi`. Se è collegata un'immagine, la presenza dell'immagine viene evidenziata e l'input `IMAGE` viene valutato durante l'aggiornamento.
6. Avvia una sessione e usa il pannello chat.
7. Clicca una risposta dell’agente per evidenziarla. `Approva prompt` userà quella risposta; se nessuna risposta è evidenziata, userà automaticamente l’ultima risposta dell’agente.
8. Se la risposta è nel formato JSON `{PROMPT, SUGGERIMENTI}`, viene inserito nel campo `Prompt approvato` solo il valore di `PROMPT`.
9. Premi `Metti in coda` oppure usa la coda normale di ComfyUI.

La chat live non inserisce richieste nella queue tramite `/prompt`; usa le route
HTTP locali del nodo. `Prepare encoder` usa una partial execution del solo ramo
necessario per raggiungere il nodo.

## Database

SQLite viene creato nella directory utente di ComfyUI sotto:

```text
user/prompt_negotiator/prompt_negotiator.sqlite3
```

Sono persistiti sessioni, messaggi e revisioni del prompt approvato.

## Test

I test automatici non richiedono un modello generativo reale:

```text
python -m unittest discover -s tests -v
```

Il test live con un CLIP generativo reale richiede un CLIP prodotto dal workflow e compatibile con
la generazione testuale (`generate()`) e con l'encoding finale. Il nodo non contiene alcun model loader.


## Analisi immagini

Il nodo espone un input `IMAGE` opzionale e **lazy**. La presenza dell'immagine non è necessaria per preparare il text encoder e non limita il nodo ai workflow I2I. `Prepara / aggiorna` valuta esclusivamente il ramo `CLIP`; l'input `IMAGE` viene valutato soltanto quando si preme **Aggiorna immagine**. La chat live usa poi l'immagine già associata al runtime tramite `clip.tokenize(..., image=image)`. Non viene effettuato upload HTTP dell'immagine e l'immagine non viene duplicata nel database.

Con Qwen3-VL vengono inseriti i token vision/image-pad previsti dal tokenizer ComfyUI; con Gemma/LTX vengono usati i marker multimodali previsti dal percorso nativo `TextGenerateLTX2Prompt`.


## Aggiornamento modello e immagine

`Prepara / aggiorna` forza una partial execution del ramo `CLIP` e **non valuta l'input `IMAGE`**. Prima della preparazione il runtime precedente viene invalidato e il relativo CLIP patcher viene rilasciato dal model manager di ComfyUI. Questo permette di cambiare text encoder senza dover prima generare una risposta e senza dover fornire un'immagine.

`Aggiorna nodi` richiede esplicitamente la riesecuzione del Prompt Negotiator e delle dipendenze collegate necessarie usando la normale cache di ComfyUI, senza invalidare il `CLIP` già preparato. L'input `IMAGE` resta lazy e viene valutato quando il socket è collegato.

## Database web

Il database non è più un nodo del workflow. È una UI web richiamabile dal menu `Prompt Negotiator` di ComfyUI. Non ha input, output, socket o collegamenti e non partecipa alla Queue: le operazioni sono HTTP dirette sulla SQLite locale nella directory `user/prompt_negotiator/`.

La UI consente di elencare le sessioni, aprirne una, modificarne titolo/system prompt/prompt finale, visualizzare i messaggi ed eliminare la sessione.

### Parser automatico del system prompt

Quando `response_mode` è `parser` (default), il nodo aggiunge automaticamente in coda al system prompt dell'utente le istruzioni per produrre un unico JSON con `PROMPT` e `SUGGERIMENTI`. Il campo `system_prompt` dell'utente è quindi facoltativo. Il testo aggiunto è derivato a runtime e non viene salvato dentro il system prompt della sessione, evitando duplicazioni al reload. In modalità `normal` non viene aggiunta alcuna istruzione.
