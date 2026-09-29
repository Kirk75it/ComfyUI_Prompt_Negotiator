import { app } from "../../scripts/app.js";

export function onApiEvent(name, handler) {
    app.api.addEventListener(name, handler);
    return () => app.api.removeEventListener(name, handler);
}
