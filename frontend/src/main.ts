import { configureHtmx } from "./htmx-setup";
import { initFlashMessages } from "./flash";
import { initConfirmDialogs } from "./confirm";

/** Boot all frontend behaviors. */
function init(): void {
  configureHtmx();
  initFlashMessages();
  initConfirmDialogs();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
