import { app } from "../../scripts/app.js";
import { encoderStatus, invalidateEncoder, requestNodesRefresh } from "./api.js";
import { onApiEvent } from "./events.js";
import { setStatus } from "./dom.js";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function updateImageStatus(ui, available) {
    if (!ui.imageStatus) return;
    ui.imageStatus.textContent = available ? "Immagine collegata" : "Nessuna immagine";
    ui.imageStatus.className = available ? "pn-image-status pn-image-ready" : "pn-image-status";
}

export async function invalidateNodeEncoder(nodeId, state, ui) {
    try {
        await invalidateEncoder(nodeId);
    } catch (_) {
        // The local runtime is invalidated in any case; backend cleanup is best effort.
    }
    state.encoder = {
        state: "UNPREPARED",
        generation_capable: false,
        identity: null,
        generation_error: null,
        image_available: false,
    };
    setStatus(ui, "Encoder non preparato", "info");
    updateImageStatus(ui, false);
}

export async function refreshEncoderStatus(nodeId, state, ui) {
    const result = await encoderStatus(nodeId);
    state.encoder = result;
    const identity = result.identity || {};
    if (ui.modelBadge) ui.modelBadge.textContent = identity.model_name || identity.tokenizer_name || identity.clip_type || "CLIP";
    updateImageStatus(ui, Boolean(result.image_available));
    if (result.state === "READY") {
        setStatus(ui, result.image_available ? "Encoder pronto · chat + immagine" : "Encoder pronto · chat abilitata", "ok");
    } else if (result.state === "READY_ENCODING_ONLY") {
        setStatus(ui, result.image_available ? "Encoder pronto · encoding + immagine" : "Encoder pronto · solo encoding", "warn");
    } else if (result.state === "PREPARING") {
        setStatus(ui, "Preparazione encoder...", "info");
    } else {
        setStatus(ui, "Encoder non preparato", "info");
    }
    return result;
}


function upstreamNodeIds(node) {
    const ids = new Set([String(node.id)]);
    const queue = [String(node.id)];
    const graph = node.graph;
    while (queue.length) {
        const currentId = queue.shift();
        const current = graph?._nodes_by_id?.[currentId] ?? graph?._nodes?.find?.((item) => String(item?.id) === currentId);
        if (!current) continue;
        for (const input of current.inputs || []) {
            if (!input?.link) continue;
            const link = graph?.links?.get?.(input.link) ?? graph?.links?.[input.link];
            const origin = link?.origin_id ?? link?.originId;
            if (origin === undefined || origin === null) continue;
            const id = String(origin);
            if (!ids.has(id)) {
                ids.add(id);
                queue.push(id);
            }
        }
    }
    return ids;
}

export async function refreshNodes(node, state, ui) {
    if (state.preparing) return;
    if (!state.encoder || (state.encoder.state !== "READY" && state.encoder.state !== "READY_ENCODING_ONLY")) {
        throw new Error("Encoder non preparato. Esegui prima Prepara / aggiorna CLIP.");
    }

    state.preparing = true;
    setStatus(ui, "Aggiornamento nodi collegati...", "info");
    const trackedNodeIds = upstreamNodeIds(node);
    let lastExecutionError = null;
    const cleanup = onApiEvent("execution_error", ({ detail }) => {
        const errorNodeId = String(detail?.node ?? detail?.node_id ?? "");
        if (!trackedNodeIds.has(errorNodeId)) return;
        lastExecutionError = detail?.exception_message || detail?.message || "Errore durante l'aggiornamento dei nodi collegati.";
    });

    try {
        await requestNodesRefresh(node.id);
        // Target the Prompt Negotiator itself so ComfyUI evaluates all
        // connected upstream dependencies. We deliberately do not invalidate
        // the prepared CLIP; unchanged dependencies remain cacheable.
        const queued = await app.queuePrompt(0, 1, { queueNodeIds: [String(node.id)] });
        if (!queued) {
            throw new Error("ComfyUI non ha accettato l'aggiornamento dei nodi collegati.");
        }

        const deadline = Date.now() + 10 * 60 * 1000;
        while (Date.now() < deadline) {
            if (lastExecutionError) throw new Error(lastExecutionError);
            const status = await refreshEncoderStatus(node.id, state, ui);
            if (status.state === "READY" || status.state === "READY_ENCODING_ONLY") {
                return status;
            }
            await sleep(250);
        }
        throw new Error("Timeout durante l'aggiornamento dei nodi collegati.");
    } finally {
        cleanup?.();
        state.preparing = false;
    }
}

export async function prepareEncoder(node, state, ui) {
    if (state.preparing) return;
    state.preparing = true;
    setStatus(ui, "Preparazione encoder...", "info");
    let cleanup = null;
    let lastExecutionError = null;
    let preparePromptId = null;

    try {
        await invalidateNodeEncoder(node.id, state, ui);

        // Register execution_error BEFORE queuePrompt so fast failures cannot be missed.
        cleanup = onApiEvent("execution_error", ({ detail }) => {
            const nodeId = String(detail?.node ?? detail?.node_id ?? "");
            const eventPromptId = String(detail?.prompt_id ?? detail?.promptId ?? "");
            if (nodeId !== String(node.id)) return;
            if (preparePromptId && eventPromptId && eventPromptId !== preparePromptId) return;
            lastExecutionError = detail?.exception_message || detail?.message || "Errore di esecuzione durante Prepare Encoder.";
        });

        // ComfyUI identifies partial-execution targets by execution-id strings.
        // LiteGraph node.id is numeric in the normal root graph, so normalize it.
        // queuePrompt() returns a boolean, not the prompt object; do not read
        // prompt_id from its return value.
        const executionNodeId = String(node.id);
        const queued = await app.queuePrompt(0, 1, {
            queueNodeIds: [executionNodeId],
        });
        if (!queued) {
            throw new Error(
                "ComfyUI non ha accettato la Prepare (queue già in elaborazione o richiesta rifiutata)."
            );
        }

        const deadline = Date.now() + 10 * 60 * 1000;
        while (Date.now() < deadline) {
            if (lastExecutionError) throw new Error(lastExecutionError);
            const status = await refreshEncoderStatus(node.id, state, ui);
            if (status.state === "READY" || status.state === "READY_ENCODING_ONLY") {
                return status;
            }
            await sleep(250);
        }
        throw new Error("Timeout durante la preparazione dell'encoder.");
    } finally {
        cleanup?.();
        state.preparing = false;
    }
}
