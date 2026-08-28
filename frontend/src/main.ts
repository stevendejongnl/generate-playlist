import { configureHtmx } from "./htmx-setup";
import { initFlashMessages } from "./flash";
import { initConfirmDialogs } from "./confirm";
import { initNavToggle } from "./nav-toggle";

/** Boot all frontend behaviors. */
function init(): void {
  configureHtmx();
  initFlashMessages();
  initConfirmDialogs();
  initNavToggle();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
