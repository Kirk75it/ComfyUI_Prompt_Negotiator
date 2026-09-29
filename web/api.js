import { app } from "../../scripts/app.js";

async function request(path, options = {}) {
    const response = await app.api.fetchApi(path, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
    });

    let payload = null;
    try {
        payload = await response.json();
    } catch (_) {
        payload = null;
    }

    if (!response.ok || !payload?.ok) {
        const message = payload?.error?.message || `HTTP ${response.status}`;
        const error = new Error(message);
        error.code = payload?.error?.code || "HTTP_ERROR";
        error.status = response.status;
        throw error;
    }
    return payload;
}

function json(path, method, body) {
    return request(path, {
        method,
        body: JSON.stringify(body),
    });
}

export function createSession(payload) {
    return json("/prompt_negotiator/sessions", "POST", payload);
}

export function listSessions(limit = 100) {
    return request(`/prompt_negotiator/sessions?limit=${encodeURIComponent(limit)}`);
}

export function getSession(sessionId) {
    return request(`/prompt_negotiator/sessions/${encodeURIComponent(sessionId)}`);
}

export function updateSession(sessionId, payload) {
    return json(`/prompt_negotiator/sessions/${encodeURIComponent(sessionId)}`, "PUT", payload);
}

export function approvePrompt(sessionId, payload) {
    return json(`/prompt_negotiator/sessions/${encodeURIComponent(sessionId)}/approve`, "POST", payload);
}

export function sendChat(payload) {
    return json("/prompt_negotiator/chat", "POST", payload);
}

export function encoderStatus(nodeId) {
    return request(`/prompt_negotiator/encoder/status?node_id=${encodeURIComponent(nodeId)}`);
}

export function invalidateEncoder(nodeId) {
    return json("/prompt_negotiator/encoder/invalidate", "POST", { node_id: String(nodeId) });
}

export function requestNodesRefresh(nodeId) {
    return json("/prompt_negotiator/encoder/refresh-nodes", "POST", { node_id: String(nodeId) });
}
