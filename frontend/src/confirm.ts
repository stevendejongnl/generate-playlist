let initialized = false;

/**
 * Intercept HTMX requests on elements with [data-confirm] and show
 * a native browser confirm dialog before proceeding.
 */
export function initConfirmDialogs(): void {
  if (initialized) return;
  initialized = true;

  document.body.addEventListener("htmx:confirm", ((evt: CustomEvent) => {
    const target = evt.target as HTMLElement;
    const message = target.getAttribute("data-confirm");
    if (!message) return;

    evt.preventDefault();
    if (window.confirm(message)) {
      (evt.detail as { issueRequest: (skipConfirm: boolean) => void }).issueRequest(true);
    }
  }) as EventListener);
}
