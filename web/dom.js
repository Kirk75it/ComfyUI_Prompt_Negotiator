function el(tag, className = "", text = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
}

function copyIconButton() {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "pn-copy-button";
    button.setAttribute("aria-label", "Copia messaggio");
    button.title = "Copia messaggio";
    button.innerHTML = `
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <rect x="8" y="8" width="11" height="11" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
            <path d="M16 8V6.5A2.5 2.5 0 0 0 13.5 4H6.5A2.5 2.5 0 0 0 4 6.5v7A2.5 2.5 0 0 0 6.5 16H8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
        </svg>`;
    return button;
}

function formatTimestamp(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString(undefined, {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function stripJsonFence(text) {
    const value = String(text || "").trim();
    const match = value.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
    return match ? match[1].trim() : value;
}

function findJsonObject(text) {
    const value = stripJsonFence(text);
    for (let start = 0; start < value.length; start += 1) {
        if (value[start] !== "{") continue;
        let depth = 0;
        let inString = false;
        let escaped = false;
        for (let i = start; i < value.length; i += 1) {
            const ch = value[i];
            if (inString) {
                if (escaped) {
                    escaped = false;
                } else if (ch === "\\") {
                    escaped = true;
                } else if (ch === '"') {
                    inString = false;
                }
                continue;
            }
            if (ch === '"') {
                inString = true;
                continue;
            }
            if (ch === "{") depth += 1;
            if (ch === "}") {
                depth -= 1;
                if (depth !== 0) continue;
                try {
                    const candidate = JSON.parse(value.slice(start, i + 1));
                    if (candidate && typeof candidate === "object" && !Array.isArray(candidate)) {
                        return candidate;
                    }
                } catch (_) {}
                break;
            }
        }
    }
    return null;
}

function normalizeSuggestions(value) {
    if (Array.isArray(value)) {
        return value.map((item) => String(item || "").trim()).filter(Boolean);
    }
    const text = String(value || "").trim();
    return text ? [text] : [];
}

function parseStructuredAssistantResponse(content) {
    const data = findJsonObject(content);
    if (!data) return null;
    const promptKey = Object.keys(data).find((key) => key.toLowerCase() === "prompt");
    const suggestionsKey = Object.keys(data).find((key) => key.toLowerCase() === "suggerimenti");
    const prompt = promptKey == null ? "" : String(data[promptKey] ?? "").trim();
    if (!prompt) return null;
    return { prompt, suggestions: normalizeSuggestions(suggestionsKey == null ? null : data[suggestionsKey]) };
}

function assistantDisplayParts(message) {
    const metadata = message.metadata || {};
    const mode = String(metadata.response_mode || "parser").trim().toLowerCase();
    let prompt = String(metadata.prompt || "").trim();
    let suggestions = normalizeSuggestions(metadata.suggestions);

    // Parser mode always has a client-side fallback. This is important when
    // loading older sessions or when a response arrives without structured
    // metadata: the raw JSON is still present in message.content.
    if (mode === "parser") {
        const parsed = parseStructuredAssistantResponse(message.content);
        if (parsed) {
            prompt = parsed.prompt;
            suggestions = parsed.suggestions;
        }
    }

    if (!prompt || mode === "normal") {
        return { prompt: String(message.content || ""), suggestions: mode === "normal" ? [] : suggestions };
    }
    return { prompt, suggestions };
}

export function createUI() {
    const root = el("div", "pn-root");

    const header = el("div", "pn-header");
    const title = document.createElement("input");
    title.className = "pn-title";
    title.type = "text";
    title.placeholder = "Nuova sessione";
    title.maxLength = 120;
    header.append(title);

    const status = el("span", "pn-status", "Encoder non preparato");
    const imageStatus = el("span", "pn-image-status", "Nessuna immagine");
    const modelBadge = el("span", "pn-model-badge", "CLIP");
    header.append(status, imageStatus, modelBadge);
    root.append(header);

    const actions = el("div", "pn-actions");
    const newButton = button("Nuova", "pn-secondary");
    const saveButton = button("Salva", "pn-secondary");
    const loadButton = button("Carica", "pn-secondary");
    const prepareButton = button("Prepara / aggiorna CLIP", "pn-primary");
    const refreshNodesButton = button("Aggiorna nodi", "pn-secondary");
    const approveButton = button("Approva prompt", "pn-primary");
    const queueButton = button("Metti in coda", "pn-success");
    actions.append(newButton, saveButton, loadButton, prepareButton, refreshNodesButton, approveButton, queueButton);
    root.append(actions);

    const messages = el("div", "pn-messages");
    root.append(messages);

    const promptRow = el("div", "pn-prompt-row");
    const promptLabel = el("div", "pn-label", "Prompt approvato");
    const prompt = document.createElement("textarea");
    prompt.className = "pn-approved-prompt";
    prompt.rows = 5;
    prompt.placeholder = "Il prompt che verrà passato al normale percorso CLIPTextEncode...";
    promptRow.append(promptLabel, prompt);
    root.append(promptRow);

    const chatRow = el("div", "pn-chat-row");
    const message = document.createElement("textarea");
    message.className = "pn-chat-input";
    message.rows = 4;
    message.placeholder = "Scrivi il messaggio...";
    const sendButton = button("Invia", "pn-primary pn-send");
    chatRow.append(message, sendButton);
    root.append(chatRow);

    const modal = el("div", "pn-modal pn-hidden");
    const modalBox = el("div", "pn-modal-box");
    const modalHeader = el("div", "pn-modal-header");
    modalHeader.append(el("strong", "", "Carica sessione"));
    const closeButton = button("Chiudi", "pn-secondary");
    modalHeader.append(closeButton);
    const list = el("div", "pn-session-list");
    modalBox.append(modalHeader, list);
    modal.append(modalBox);
    root.append(modal);

    return {
        root,
        title,
        status,
        imageStatus,
        modelBadge,
        newButton,
        saveButton,
        loadButton,
        prepareButton,
        refreshNodesButton,
        approveButton,
        queueButton,
        messages,
        prompt,
        message,
        sendButton,
        modal,
        closeButton,
        list,
    };
}

function button(text, className) {
    const node = document.createElement("button");
    node.type = "button";
    node.textContent = text;
    node.className = `pn-button ${className || ""}`.trim();
    return node;
}

export function renderMessages(ui, messages, selectedSequence = null, onSelectMessage = null) {
    const selectHandler = onSelectMessage || ui.messageSelectionHandler || null;
    ui.messages.replaceChildren();
    for (const message of messages) {
        const row = el("article", `pn-message ${message.role === "user" ? "pn-user" : "pn-assistant"}`);
        const sequence = Number(message.sequence);
        const selectable = message.role === "assistant" && Number.isFinite(sequence) && sequence > 0;
        if (selectable) {
            row.classList.add("pn-selectable");
            row.title = "Clicca per selezionare questa risposta come prompt da approvare";
            if (sequence === Number(selectedSequence)) row.classList.add("pn-selected");
            row.addEventListener("click", () => selectHandler?.(sequence));
        }

        const top = el("div", "pn-message-top");
        const label = el("div", "pn-message-role", message.role === "user" ? "Tu" : "Agente");
        const timestamp = el("time", "pn-message-time", formatTimestamp(message.created_at));
        top.append(label, timestamp);

        const copyButton = copyIconButton();
        const display = message.role === "assistant" ? assistantDisplayParts(message) : { prompt: String(message.content || ""), suggestions: [] };
        const copyText = message.role === "assistant"
            ? [display.prompt, ...display.suggestions.map((value) => `• ${value}`)].filter(Boolean).join("\n\n")
            : display.prompt;
        copyButton.addEventListener("click", async (event) => {
            event.preventDefault();
            event.stopPropagation();
            try {
                await navigator.clipboard.writeText(copyText);
                copyButton.classList.add("pn-copied");
                window.setTimeout(() => copyButton.classList.remove("pn-copied"), 900);
            } catch (_) {
                // Clipboard permissions are browser-dependent; do not turn a copy
                // failure into a chat error.
            }
        });
        top.append(copyButton);

        row.append(top);

        if (message.role === "assistant" && display.prompt) {
            const promptBlock = el("div", "pn-message-prompt", display.prompt);
            row.append(promptBlock);
            if (display.suggestions.length) {
                const suggestionWrap = el("div", "pn-suggestions");
                const suggestionTitle = el("div", "pn-suggestions-title", "Suggerimenti");
                suggestionWrap.append(suggestionTitle);
                for (const suggestion of display.suggestions) {
                    suggestionWrap.append(el("div", "pn-suggestion", suggestion));
                }
                row.append(suggestionWrap);
            }
        } else {
            const body = el("div", "pn-message-body", display.prompt);
            row.append(body);
        }
        ui.messages.append(row);
    }
    ui.messages.scrollTop = ui.messages.scrollHeight;
}

export function setStatus(ui, text, kind = "info") {
    ui.status.textContent = text;
    ui.status.className = `pn-status pn-status-${kind}`;
}

export function setBusy(ui, busy) {
    for (const button of [ui.newButton, ui.saveButton, ui.loadButton, ui.prepareButton, ui.refreshNodesButton, ui.approveButton, ui.queueButton, ui.sendButton]) {
        button.disabled = busy;
    }
}

export function openSessionModal(ui) {
    ui.modal.classList.remove("pn-hidden");
}

export function closeSessionModal(ui) {
    ui.modal.classList.add("pn-hidden");
}

export function renderSessionList(ui, sessions, onSelect) {
    ui.list.replaceChildren();
    if (!sessions.length) {
        ui.list.append(el("div", "pn-empty", "Nessuna sessione salvata."));
        return;
    }
    for (const session of sessions) {
        const row = document.createElement("button");
        row.type = "button";
        row.className = "pn-session-item";
        const title = document.createElement("strong");
        title.textContent = session.title;
        const meta = document.createElement("span");
        meta.textContent = `${session.model_name || "CLIP"} · ${session.updated_at}`;
        row.append(title, meta);
        row.addEventListener("click", () => onSelect(session));
        ui.list.append(row);
    }
}
