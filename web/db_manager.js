import { app } from "../../scripts/app.js";

async function api(path, options = {}) {
    const response = await app.api.fetchApi(path, {
        ...options,
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data?.error?.message || `HTTP ${response.status}`);
    return data;
}

function el(tag, cls = "", text = "") {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text) node.textContent = text;
    return node;
}

function btn(text, cls = "pn-button pn-secondary") {
    const node = el("button", cls, text);
    node.type = "button";
    return node;
}

function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

let overlay = null;
let ui = null;

function buildUI() {
    if (overlay) return;
    overlay = el("div", "pn-db-modal");
    const box = el("div", "pn-db-modal-box");
    const header = el("div", "pn-db-header");
    const titleWrap = el("div");
    titleWrap.append(el("div", "pn-db-title", "Prompt Negotiator · Database"));
    titleWrap.append(el("div", "pn-db-sub", "Gestione web delle sessioni locali"));
    const close = btn("Chiudi", "pn-button pn-secondary");
    header.append(titleWrap, close);

    const toolbar = el("div", "pn-db-toolbar");
    const refresh = btn("Aggiorna", "pn-button pn-primary");
    const status = el("span", "pn-db-sub", "");
    toolbar.append(refresh, status);

    const body = el("div", "pn-db-web-body");
    const list = el("div", "pn-db-web-list");
    const detail = el("div", "pn-db-web-detail");
    const detailTitle = el("div", "pn-db-title", "Seleziona una sessione");
    const title = document.createElement("input"); title.className = "pn-db-input"; title.placeholder = "Titolo";
    const system = document.createElement("textarea"); system.className = "pn-db-input"; system.rows = 5; system.placeholder = "System prompt";
    const final = document.createElement("textarea"); final.className = "pn-db-input"; final.rows = 6; final.placeholder = "Prompt finale approvato";
    const messagesTitle = el("div", "pn-db-section-title", "Messaggi");
    const messages = el("div", "pn-db-web-messages");
    const save = btn("Salva modifiche", "pn-button pn-success");
    save.disabled = true;
    detail.append(detailTitle, title, system, final, messagesTitle, messages, save);
    body.append(list, detail);
    box.append(header, toolbar, body);
    overlay.append(box);
    document.body.append(overlay);

    ui = { overlay, close, refresh, status, list, detail, detailTitle, title, system, final, messages, save, currentId: null };
    close.onclick = closeDatabaseManager;
    refresh.onclick = () => refreshSessions();
    overlay.addEventListener("click", (event) => {
        if (event.target === overlay) closeDatabaseManager();
    });
    save.onclick = saveCurrent;
}

function closeDatabaseManager() {
    if (overlay) overlay.classList.remove("active");
}

function openDatabaseManager() {
    buildUI();
    overlay.classList.add("active");
    void refreshSessions();
}

function renderSessions(sessions) {
    ui.list.replaceChildren();
    if (!sessions.length) {
        ui.list.append(el("div", "pn-empty", "Nessuna sessione salvata."));
        return;
    }
    for (const session of sessions) {
        const card = el("div", "pn-db-web-session-row");
        const open = el("button", "pn-db-web-session");
        open.type = "button";
        open.append(el("strong", "pn-db-card-title", session.title || "Senza titolo"));
        open.append(el("span", "pn-db-card-meta", `${session.model_name || "Modello non indicato"} · rev. ${session.revision || 0} · ${formatDate(session.updated_at)}`));
        open.onclick = () => openSession(session.id);
        const del = btn("Elimina", "pn-button pn-secondary");
        del.onclick = () => deleteSession(session.id, session.title || "Senza titolo");
        card.append(open, del);
        ui.list.append(card);
    }
}

async function refreshSessions() {
    try {
        ui.status.textContent = "Caricamento...";
        const data = await api("/prompt_negotiator/database/sessions?limit=500");
        renderSessions(data.sessions || []);
        ui.status.textContent = `${(data.sessions || []).length} sessioni`;
    } catch (error) {
        ui.status.textContent = error.message;
    }
}

async function openSession(sessionId) {
    try {
        const data = await api(`/prompt_negotiator/database/sessions/${encodeURIComponent(sessionId)}`);
        ui.currentId = sessionId;
        ui.detailTitle.textContent = data.session.title || "Senza titolo";
        ui.title.value = data.session.title || "";
        ui.system.value = data.session.system_prompt || "";
        ui.final.value = data.session.final_prompt || "";
        renderMessages(data.messages || []);
        ui.save.disabled = false;
    } catch (error) {
        ui.status.textContent = error.message;
    }
}

async function saveCurrent() {
    if (!ui.currentId) return;
    try {
        ui.save.disabled = true;
        await api(`/prompt_negotiator/database/sessions/${encodeURIComponent(ui.currentId)}`, {
            method: "PUT",
            body: JSON.stringify({
                title: ui.title.value,
                system_prompt: ui.system.value,
                final_prompt: ui.final.value,
            }),
        });
        ui.status.textContent = "Modifiche salvate";
        await refreshSessions();
        await openSession(ui.currentId);
    } catch (error) {
        ui.status.textContent = error.message;
        ui.save.disabled = false;
    }
}

async function deleteSession(sessionId, title) {
    if (!confirm(`Eliminare la sessione “${title}”?`)) return;
    try {
        await api(`/prompt_negotiator/database/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
        if (ui.currentId === sessionId) {
            ui.currentId = null;
            ui.detailTitle.textContent = "Seleziona una sessione";
            ui.title.value = "";
            ui.system.value = "";
            ui.final.value = "";
            ui.messages.replaceChildren();
            ui.save.disabled = true;
        }
        await refreshSessions();
    } catch (error) {
        ui.status.textContent = error.message;
    }
}

export function registerDatabaseFrontend() {
    app.registerExtension({
        name: "PromptNegotiatorDatabaseWeb",
        commands: [
            {
                id: "PromptNegotiator.OpenDatabase",
                label: "Prompt Negotiator · Database",
                function: openDatabaseManager,
            },
        ],
        menuCommands: [
            {
                path: ["Prompt Negotiator"],
                commands: ["PromptNegotiator.OpenDatabase"],
            },
        ],
    });
}
