export function createState(node) {
    return {
        node,
        session: null,
        messages: [],
        encoder: {
            state: "UNPREPARED",
            generation_capable: false,
            identity: null,
            generation_error: null,
            image_available: false,
        },
        busy: false,
        preparing: false,
        loading: false,
        statusText: "Encoder non preparato",
        lastGeneratedResponse: "",
        selectedMessageSequence: null,
    };
}

export function setSession(state, session, messages = []) {
    state.session = session;
    state.messages = messages;
    state.selectedMessageSequence = null;
}

export function clearSession(state) {
    state.session = null;
    state.messages = [];
    state.selectedMessageSequence = null;
}

export function currentSessionId(state) {
    return state.session?.id || "";
}
