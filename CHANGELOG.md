## 1.0.15 — System Prompt node

- Renamed the visible node from `Krea2 System Prompt` to `System Prompt`.
- The node remains file-based and model-agnostic; presets continue to live in `SystemPrompt/`.
- Preserved technical node ID `Krea2SystemPrompt` for existing workflows.
- Kept `krea2_system_prompt.py` as a Python import compatibility shim without registering a second node.

## 1.0.14 — Krea2 System Prompt file-based
- Rimosso il contenuto dei tre system prompt dal codice Python.
- `Krea2 System Prompt` legge ora i file UTF-8 `.txt` dalla cartella `SystemPrompt/`.
- La selezione del nodo viene popolata automaticamente dai nomi dei file presenti nella cartella.
- Inclusi tre preset Krea 2 iniziali derivati dalla documentazione pubblica della repository AI-KSK/krea2-prompt-suite.
- Aggiunta documentazione nella cartella `SystemPrompt/` per la personalizzazione.
- Aggiunti test per il caricamento da file e per garantire che i prompt non siano hardcoded nel modulo Python.

## 1.0.13 — Correzione chat frontend
- Corretto `connected(...)` non definito in `web/chat.js`.
- Il frontend usa `inputIsConnected(...)` per distinguere input collegati da widget locali.
- Aggiunto test di regressione.

## 1.0.12 — Aggiorna nodi

- Sostituito **Aggiorna immagine** con **Aggiorna nodi**.
- L'aggiornamento riesegue il Prompt Negotiator e le dipendenze collegate necessarie tramite la normale cache di ComfyUI, senza invalidare il CLIP preparato. citeturn997807search0turn922759search1
- I valori prodotti dai nodi esterni vengono acquisiti nel runtime, inclusi system prompt, response mode e parametri di generazione.
- L'IMAGE resta lazy e viene richiesta durante Aggiorna nodi quando il socket è collegato.
- L'indicatore dell'immagine resta visibile e viene aggiornato dopo l'esecuzione.

## 1.0.11 — automatic parser system contract

- In `parser` mode, Prompt Negotiator automatically appends a fixed JSON response contract to the user's system prompt.
- The system prompt input remains optional; with an empty field the parser contract is still sent to the model.
- The contract is appended once at runtime and is not persisted as part of the user's system prompt, preventing duplication after session reloads.
- `normal` mode sends the user's system prompt unchanged.
- Existing JSON parser behavior remains `{PROMPT, SUGGERIMENTI}` and approval uses only `PROMPT`.

## 1.0.10 — parser frontend fallback

- Il parser della risposta strutturata viene applicato anche lato frontend usando il contenuto JSON grezzo del messaggio come fallback.
- `normal` continua a mostrare la risposta senza parsing.
- `Approva prompt` continua a usare esclusivamente `PROMPT` in parser mode.

# Changelog

## 1.0.9
- Added `Krea2 System Prompt` under `Prompt Navigator`.
- Added three source-derived Krea 2 prompt types: Qwen3-VL Reverse Analyzer, RunningHub Krea2 Prompt Compiler, and Krea2 Universal Vision Creator.
- Moved `Prompt Negotiator` from `conditioning/text` to `Prompt Navigator`.

## 1.0.8

- Corretto il salvataggio delle risposte in modalità parser: il JSON grezzo generato dal modello viene conservato nel metadata della risposta.
- Il transcript usato dai round successivi mantiene quindi la struttura JSON originale invece del testo già presentato dalla UI.
- Al caricamento delle sessioni, le risposte parser legacy prive del JSON originale vengono ricostruite in un JSON canonico a partire da `PROMPT` e `SUGGERIMENTI`.
- `Approva prompt` continua a estrarre esclusivamente `PROMPT`, anche dopo il caricamento di una sessione.

# Changelog

## 1.0.6
- Aggiunta la scelta `response_mode`: `parser` è attivo di default e interpreta il formato `{PROMPT, SUGGERIMENTI}`; `normal` lascia la risposta del modello completamente intatta per parser personalizzati nel workflow.
- In modalità `normal`, `Approva prompt` usa l'intero messaggio dell'agente; in modalità `parser` approva solo `PROMPT`.
- Il transcript inviato al modello continua a conservare sempre la risposta originale.
- Rimosso il nodo workflow `Prompt Negotiator · Database`: la gestione del database è ora una UI web richiamabile dal menu `Prompt Negotiator`, senza socket, widget o partecipazione alla Queue.
- La UI Database consente elenco, selezione, modifica, visualizzazione dei messaggi ed eliminazione delle sessioni.


## 1.0.5
- Le risposte dell'agente possono essere strutturate come JSON `{PROMPT, SUGGERIMENTI}`. Il JSON grezzo resta nel transcript, mentre la UI mostra solo il prompt e i suggerimenti in forma leggibile.
- `Approva prompt` non riutilizza più il primo prompt approvato: usa il messaggio agente evidenziato oppure, se nessuno è evidenziato, l'ultima risposta dell'agente. Il server approva tramite `message_sequence`.
- Ogni messaggio visualizza data/ora, e le risposte dell'agente sono cliccabili per la selezione. Cliccando di nuovo sulla risposta selezionata la selezione viene rimossa.
- Aggiunta icona copia a ogni messaggio, con copia del contenuto visualizzato.
- Le sessioni caricate ricostruiscono anche i dati strutturati delle risposte precedenti, senza perdere lo storico.


## 1.0.4
- Corretto il refresh dell'input `IMAGE`: il nodo interattivo ora usa un fingerprint runtime sempre nuovo, così ComfyUI non riutilizza l'output cache precedente dello stesso `PromptNegotiator`.
- `Aggiorna immagine` forza quindi una nuova esecuzione di `check_lazy_status()` e può rendere effettivamente attivo il collegamento `IMAGE`.
- Aggiunto test dedicato alla riesecuzione interattiva.

# Prompt Negotiator v1.0.3

- Rimosso il rilascio manuale del `ModelPatcher` dal runtime registry.
- `invalidate()`, scadenza TTL e cleanup eliminano soltanto il riferimento runtime; non chiamano più le API di unload/detach/unpatch di ComfyUI.
- Corretto il percorso di riesecuzione dei text encoder quantizzati che poteva causare `RuntimeError: Cannot set version_counter for inference tensor` al secondo caricamento.
- Aggiornati README e test di regressione.

# Prompt Negotiator v1.0.2

- Corretto il bug per cui `execute()` richiedeva obbligatoriamente l'input `IMAGE` anche quando non valutato dalla lazy evaluation.
- `IMAGE` resta realmente opzionale: Prepare/aggiorna encoder può eseguire il nodo senza valutare l'immagine.
- Aggiunto test di regressione sulla firma di `execute()`.

## 1.0.1

- Reso l'input `IMAGE` opzionale e lazy.
- `Prepara / aggiorna` prepara esclusivamente il text encoder e non valuta l'immagine.
- `Aggiorna immagine` richiede esplicitamente la valutazione dell'input `IMAGE` tramite `check_lazy_status()`.
- Il runtime preserva l'immagine precedente quando un'esecuzione normale non la valuta.
- Separato il ciclo di vita del CLIP da quello del contesto immagine.
- Aggiunte route e test per la richiesta esplicita di aggiornamento immagine.

## 1.0.0

- Prima versione pubblica del Prompt Negotiator.
