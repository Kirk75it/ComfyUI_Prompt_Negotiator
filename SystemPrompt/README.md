# SystemPrompt

Questa cartella contiene i system prompt usati dal nodo **System Prompt**.

Il nodo legge tutti i file `.txt` presenti qui, usa il nome del file senza estensione come voce della selezione e restituisce il contenuto del file come `STRING`.

Per aggiungere un nuovo system prompt:

1. crea un file `.txt` in UTF-8;
2. inseriscilo in questa cartella;
3. riavvia o ricarica i nodi di ComfyUI per far comparire il nuovo nome nella selezione.

Il contenuto dei file può essere modificato senza modificare Python.

## Preset iniziali Krea 2

- `qwen3vl-reverse-analyzer.txt`
- `runninghub-krea2-compiler.txt`
- `krea2-universal-vision-creator.txt`

I tre preset sono versioni operative derivate dalla documentazione pubblica della repository:
https://github.com/AI-KSK/krea2-prompt-suite
