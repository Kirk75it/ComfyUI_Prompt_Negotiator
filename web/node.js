import { app } from "../../scripts/app.js";
import { createUI, closeSessionModal, openSessionModal, renderMessages, setStatus } from "./dom.js";
import { createState } from "./state.js";
import { createNewSession, openLoadDialog, resetState, saveCurrentSession, setWorkflowWidget } from "./session.js";
import { sendMessage } from "./chat.js";
import { approvePrompt } from "./api.js";
import { prepareEncoder, refreshNodes, invalidateNodeEncoder, refreshEncoderStatus } from "./encoder.js";
import { currentSessionId } from "./state.js";

function wrapConnectionInvalidation(node, state, ui) {
    if (node.__promptNegotiatorConnectionsWrapped) return;
    const original = node.onConnectionsChange;
    node.onConnectionsChange = function(type, slotIndex, isConnected, linkInfo, ioSlot) {
        if (original) {
            original.call(this, type, slotIndex, isConnected, linkInfo, ioSlot);
        }
        const clipIndex = this.inputs?.findIndex((input) => input.name === "clip") ?? -1;
        const imageIndex = this.inputs?.findIndex((input) => input.name === "image") ?? -1;
        if (slotIndex === clipIndex) {
            void invalidateNodeEncoder(this.id, state, ui);
        } else if (slotIndex === imageIndex && !isConnected) {
            if (ui.imageStatus) {
                ui.imageStatus.textContent = "Nessuna immagine";
                ui.imageStatus.className = "pn-image-status";
            }
        }
    };
    node.__promptNegotiatorConnectionsWrapped = true;
}

function selectMessageForApproval(state, ui, sequence) {
    const current = Number(state.selectedMessageSequence);
    state.selectedMessageSequence = current === Number(sequence) ? null : Number(sequence);
    renderMessages(ui, state.messages, state.selectedMessageSequence);
    if (state.selectedMessageSequence === null) {
        setStatus(ui, "Nessuna risposta selezionata · Approva userà l'ultima risposta dell'agente", "info");
    } else {
        setStatus(ui, "Risposta selezionata · Approva prompt userà questa risposta", "ok");
    }
}

async function approve(state, ui) {
    const sessionId = currentSessionId(state);
    if (!sessionId) throw new Error("Nessuna sessione attiva.");
    const assistantMessages = [...state.messages].filter((message) => message.role === "assistant");
    if (!assistantMessages.length) {
        throw new Error("Non esiste ancora una risposta dell'agente da approvare.");
    }

    const selected = state.selectedMessageSequence
        ? assistantMessages.find((message) => Number(message.sequence) === Number(state.selectedMessageSequence))
        : null;
    const target = selected || assistantMessages[assistantMessages.length - 1];
    if (!target) throw new Error("Nessuna risposta dell'agente disponibile.");

    const result = await approvePrompt(sessionId, {
        node_id: String(state.node.id),
        message_sequence: Number(target.sequence),
        model_name: state.encoder.identity?.model_name || null,
        clip_type: state.encoder.identity?.clip_type || null,
    });
    state.session = result.session;
    ui.prompt.value = result.session.final_prompt || "";
    setWorkflowWidget(state.node, "approved_prompt", result.session.final_prompt || "");
    setStatus(ui, `Prompt approvato · messaggio ${result.message_sequence} · revisione ${result.revision}`, "ok");
}

function bindUI(node, state, ui) {
    ui.newButton.addEventListener("click", async () => {
        try {
            await createNewSession(state, ui);
            setStatus(ui, "Nuova sessione", "ok");
        } catch (error) {
            setStatus(ui, error.message, "error");
        }
    });

    ui.saveButton.addEventListener("click", async () => {
        try {
            await saveCurrentSession(state, ui);
            setStatus(ui, "Sessione salvata", "ok");
        } catch (error) {
            setStatus(ui, error.message, "error");
        }
    });

    ui.loadButton.addEventListener("click", async () => {
        try {
            openSessionModal(ui);
            await openLoadDialog(state, ui);
        } catch (error) {
            closeSessionModal(ui);
            setStatus(ui, error.message, "error");
        }
    });

    ui.closeButton.addEventListener("click", () => closeSessionModal(ui));
    ui.prepareButton.addEventListener("click", async () => {
        try {
            await prepareEncoder(node, state, ui);
        } catch (error) {
            setStatus(ui, error.message, "error");
        }
    });

    ui.refreshNodesButton.addEventListener("click", async () => {
        try {
            await refreshNodes(node, state, ui);
        } catch (error) {
            setStatus(ui, error.message, "error");
        }
    });

    ui.approveButton.addEventListener("click", async () => {
        try {
            await approve(state, ui);
        } catch (error) {
            setStatus(ui, error.message, "error");
        }
    });

    ui.queueButton.addEventListener("click", async (event) => {
        event.preventDefault();
        event.stopPropagation();
        try {
            if (!ui.prompt.value.trim()) throw new Error("Il prompt approvato è vuoto.");
            setWorkflowWidget(node, "approved_prompt", ui.prompt.value);
            await app.queuePrompt(0, 1);
            setStatus(ui, "Workflow messo in coda", "ok");
        } catch (error) {
            setStatus(ui, error.message, "error");
        }
    });

    ui.sendButton.addEventListener("click", async (event) => {
        event.preventDefault();
        event.stopPropagation();
        try {
            await sendMessage(state, ui);
        } catch (_) {}
    });

    // Capture the keyboard event on the chat textarea and stop it from
    // bubbling to ComfyUI's global keybinding handler. Without this, Enter
    // can be interpreted as the global Queue command and creates a zero-time
    // ComfyUI job instead of remaining a chat-only action.
    ui.message.addEventListener("keydown", async (event) => {
        if (event.isComposing) return;
        if (event.key !== "Enter") return;

        // Shift+Enter intentionally remains a newline inside the textarea.
        if (event.shiftKey) return;

        event.preventDefault();
        event.stopPropagation();

        try {
            console.debug("[PromptNegotiator] chat Enter -> sendMessage");
            await sendMessage(state, ui);
        } catch (error) {
            console.error("[PromptNegotiator] sendMessage failed", error);
        }
    }, true);

    ui.title.addEventListener("change", async () => {
        if (!state.session) return;
        try {
            await saveCurrentSession(state, ui);
        } catch (error) {
            setStatus(ui, error.message, "error");
        }
    });

    ui.prompt.addEventListener("input", () => {
        setWorkflowWidget(node, "approved_prompt", ui.prompt.value);
    });
}

export function installNodeUI(node) {
    if (node.__promptNegotiatorInstalled) return;
    node.__promptNegotiatorInstalled = true;

    const ui = createUI();
    const state = createState(node);
    node.__promptNegotiatorState = state;
    node.__promptNegotiatorUI = ui;

    node.setSize?.([720, 760]);
    if (typeof node.addDOMWidget === "function") {
        node.addDOMWidget("prompt_negotiator_chat", "custom", ui.root, {
            serialize: false,
            hideOnZoom: false,
        });
    } else {
        node.addWidget("text", "prompt_negotiator_chat", "Frontend DOM widget non disponibile", () => {}, {});
    }

    ui.messageSelectionHandler = (sequence) => selectMessageForApproval(state, ui, sequence);
    bindUI(node, state, ui);
    wrapConnectionInvalidation(node, state, ui);
    renderMessages(ui, [], null, ui.messageSelectionHandler);
    void refreshEncoderStatus(node.id, state, ui).catch(() => {
        setStatus(ui, "Encoder non preparato", "info");
    });
}

export function registerFrontend() {
    app.registerExtension({
        name: "PromptNegotiator",
        async nodeCreated(node) {
            if (node.type === "PromptNegotiator" || node.comfyClass === "PromptNegotiator") {
                installNodeUI(node);
            }
        },
    });
}
