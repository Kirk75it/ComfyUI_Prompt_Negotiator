import { sendChat } from "./api.js";
import { renderMessages, setBusy, setStatus } from "./dom.js";
import { currentSessionId } from "./state.js";
import { inputIsConnected, readWorkflowInputs } from "./session.js";

export async function sendMessage(state, ui) {
    const message = ui.message.value.trim();
    if (!message || state.busy) return;
    if (!currentSessionId(state)) {
        throw new Error("Crea o carica una sessione prima di inviare un messaggio.");
    }
    if (state.encoder.state !== "READY" || !state.encoder.generation_capable) {
        throw new Error("Il CLIP generativo non è pronto. Esegui Preparazione encoder.");
    }

    state.busy = true;
    setBusy(ui, true);
    setStatus(ui, "Generazione in corso...", "info");
    const inputs = readWorkflowInputs(state.node);
    try {
        const result = await sendChat({
            node_id: String(state.node.id),
            session_id: currentSessionId(state),
            message,
            system_prompt: inputIsConnected(state.node, "system_prompt") ? null : inputs.system_prompt,
            response_mode: inputIsConnected(state.node, "response_mode") ? null : inputs.response_mode,
            max_history_messages: inputIsConnected(state.node, "max_history_messages") ? null : inputs.max_history_messages,
            max_length: inputIsConnected(state.node, "max_length") ? null : inputs.max_length,
            sampling_mode: inputIsConnected(state.node, "sampling_mode") ? null : (typeof inputs.sampling_mode === "object" ? "off" : String(inputs.sampling_mode)),
            temperature: inputIsConnected(state.node, "temperature") ? null : inputs.temperature,
            top_k: inputIsConnected(state.node, "top_k") ? null : inputs.top_k,
            top_p: inputIsConnected(state.node, "top_p") ? null : inputs.top_p,
            min_p: inputIsConnected(state.node, "min_p") ? null : inputs.min_p,
            repetition_penalty: inputIsConnected(state.node, "repetition_penalty") ? null : inputs.repetition_penalty,
            presence_penalty: inputIsConnected(state.node, "presence_penalty") ? null : inputs.presence_penalty,
            mtp: inputIsConnected(state.node, "mtp") ? null : inputs.mtp,
            thinking: inputIsConnected(state.node, "thinking") ? null : inputs.thinking,
            use_default_template: inputIsConnected(state.node, "use_default_template") ? null : inputs.use_default_template,
            seed: inputIsConnected(state.node, "seed") ? null : inputs.seed,
        });

        // The server returns the authoritative persisted records, including
        // sequence numbers, timestamps and structured assistant metadata.
        state.messages.push(result.user_message);
        state.messages.push(result.assistant_message);
        state.lastGeneratedResponse = result.response || "";
        // A newly generated answer invalidates an older explicit selection.
        // With no selection, Approva prompt uses the newest assistant message.
        state.selectedMessageSequence = null;

        ui.message.value = "";
        renderMessages(ui, state.messages, state.selectedMessageSequence);
        setStatus(ui, "Encoder pronto · chat abilitata", "ok");
    } catch (error) {
        console.error("[PromptNegotiator] chat generation failed", error);
        setStatus(ui, error.message || "Errore di generazione.", "error");
        throw error;
    } finally {
        state.busy = false;
        setBusy(ui, false);
    }
}
