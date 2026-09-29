import { createSession, getSession, listSessions, updateSession } from "./api.js";
import { clearSession, setSession } from "./state.js";
import { closeSessionModal, renderMessages, renderSessionList } from "./dom.js";

function nodeWidget(node, name) {
    return node.widgets?.find((widget) => widget.name === name) || null;
}

function widgetValue(node, name, fallback = "") {
    const widget = nodeWidget(node, name);
    if (!widget) return fallback;
    try {
        if (typeof widget.getValue === "function") return widget.getValue();
    } catch (_) {}
    return widget.value ?? fallback;
}

export function readWorkflowInputs(node) {
    return {
        system_prompt: String(widgetValue(node, "system_prompt", "") || ""),
        final_prompt: String(widgetValue(node, "approved_prompt", "") || ""),
        response_mode: String(widgetValue(node, "response_mode", "parser") || "parser"),
        max_history_messages: Number(widgetValue(node, "max_history_messages", 8) || 8),
        max_length: Number(widgetValue(node, "max_length", 512) || 512),
        sampling_mode: widgetValue(node, "sampling_mode", "off"),
        temperature: Number(widgetValue(node, "temperature", 0.7) ?? 0.7),
        top_k: Number(widgetValue(node, "top_k", 64) ?? 64),
        top_p: Number(widgetValue(node, "top_p", 0.95) ?? 0.95),
        min_p: Number(widgetValue(node, "min_p", 0.05) ?? 0.05),
        repetition_penalty: Number(widgetValue(node, "repetition_penalty", 1.05) ?? 1.05),
        presence_penalty: Number(widgetValue(node, "presence_penalty", 0) ?? 0),
        mtp: String(widgetValue(node, "mtp", "auto") ?? "auto"),
        thinking: Boolean(widgetValue(node, "thinking", false)),
        use_default_template: Boolean(widgetValue(node, "use_default_template", true)),
        seed: Number(widgetValue(node, "seed", 0) || 0),
    };
}

export function inputIsConnected(node, name) {
    const input = node.inputs?.find((item) => item?.name === name);
    return Boolean(input?.link || (input?.links && input.links.length));
}

export function setWorkflowWidget(node, name, value) {
    const widget = nodeWidget(node, name);
    if (!widget) return false;

    // ComfyUI frontend 1.52.x exposes BaseWidget.setValue(value, context),
    // where the second argument is required because the implementation
    // destructures { e, node, canvas }. Calling setValue(value) therefore
    // throws exactly: 'Cannot destructure property 'e' of 'undefined''.
    // For programmatic workflow updates we do not have a pointer event, so
    // update the widget value directly and then invoke its callback.
    widget.value = value;
    widget.callback?.(value);

    node.graph?.incrementVersion?.();
    node.graph?.setDirtyCanvas?.(true, true);
    return true;
}

export async function createNewSession(state, ui) {
    const inputs = readWorkflowInputs(state.node);
    const result = await createSession({
        title: "Nuova sessione",
        system_prompt: inputs.system_prompt,
        final_prompt: inputs.final_prompt,
        model_name: state.encoder.identity?.model_name || null,
        clip_type: state.encoder.identity?.clip_type || null,
    });
    setSession(state, result.session, []);
    state.lastGeneratedResponse = "";
    ui.title.value = result.session.title;
    ui.prompt.value = result.session.final_prompt;
    renderMessages(ui, []);
    return result.session;
}

export async function saveCurrentSession(state, ui) {
    if (!state.session) {
        await createNewSession(state, ui);
    }
    const inputs = readWorkflowInputs(state.node);
    const result = await updateSession(state.session.id, {
        title: ui.title.value,
        system_prompt: inputs.system_prompt,
        final_prompt: ui.prompt.value,
    });
    setSession(state, result.session, state.messages);
    return result.session;
}

export async function openLoadDialog(state, ui) {
    const result = await listSessions(100);
    renderSessionList(ui, result.sessions, async (session) => {
        const loaded = await getSession(session.id);
        setSession(state, loaded.session, loaded.messages);
        state.lastGeneratedResponse = [...loaded.messages].reverse().find((message) => message.role === "assistant")?.content || "";
        ui.title.value = loaded.session.title;
        ui.prompt.value = loaded.session.final_prompt;
        renderMessages(ui, loaded.messages, state.selectedMessageSequence);
        closeSessionModal(ui);
        state.node.graph?.incrementVersion?.();
    });
}

export function resetState(state, ui) {
    clearSession(state);
    ui.title.value = "";
    ui.prompt.value = "";
    renderMessages(ui, []);
}
