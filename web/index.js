import { registerFrontend } from "./node.js";
import { registerDatabaseFrontend } from "./db_manager.js";

const stylesheet = document.createElement("link");
stylesheet.rel = "stylesheet";
stylesheet.href = new URL("./styles.css", import.meta.url).href;
document.head.appendChild(stylesheet);

registerFrontend();
registerDatabaseFrontend();
