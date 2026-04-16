/**
 * Auto-dismiss flash/alert messages after a delay.
 */
export function initFlashMessages(dismissAfterMs = 5000): void {
  document.addEventListener("DOMContentLoaded", () => {
    scheduleAutoDismiss(dismissAfterMs);
  });

  // Also handle alerts injected by HTMX
  document.body.addEventListener("htmx:afterSwap", () => {
    scheduleAutoDismiss(dismissAfterMs);
  });
}

function scheduleAutoDismiss(ms: number): void {
  const alerts = document.querySelectorAll<HTMLElement>(".alert[data-auto-dismiss]");
  alerts.forEach((alert) => {
    if (alert.dataset.dismissScheduled) return;
    alert.dataset.dismissScheduled = "true";

    setTimeout(() => {
      alert.style.transition = "opacity 0.3s ease";
      alert.style.opacity = "0";
      setTimeout(() => alert.remove(), 300);
    }, ms);
  });
}
