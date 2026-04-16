import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { initFlashMessages } from "./flash";

function createAlert(text: string, autoDismiss = true): HTMLDivElement {
  const el = document.createElement("div");
  el.className = "alert";
  el.textContent = text;
  if (autoDismiss) el.setAttribute("data-auto-dismiss", "");
  return el;
}

describe("flash messages", () => {
  beforeEach(() => {
    document.body.replaceChildren();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("removes alert elements after the dismiss delay", () => {
    document.body.appendChild(createAlert("Test message"));

    initFlashMessages(1000);
    document.dispatchEvent(new Event("DOMContentLoaded"));

    expect(document.querySelector(".alert")).not.toBeNull();

    vi.advanceTimersByTime(1000);
    const alert = document.querySelector<HTMLElement>(".alert");
    expect(alert?.style.opacity).toBe("0");

    vi.advanceTimersByTime(300);
    expect(document.querySelector(".alert")).toBeNull();
  });

  it("does not dismiss alerts without data-auto-dismiss", () => {
    document.body.appendChild(createAlert("Persistent message", false));

    initFlashMessages(1000);
    document.dispatchEvent(new Event("DOMContentLoaded"));

    vi.advanceTimersByTime(2000);
    expect(document.querySelector(".alert")).not.toBeNull();
  });

  it("does not double-schedule the same alert", () => {
    document.body.appendChild(createAlert("Test"));

    initFlashMessages(1000);
    document.dispatchEvent(new Event("DOMContentLoaded"));

    const alert = document.querySelector<HTMLElement>(".alert");
    expect(alert?.dataset.dismissScheduled).toBe("true");

    document.body.dispatchEvent(new Event("htmx:afterSwap", { bubbles: true }));
    vi.advanceTimersByTime(500);
    expect(document.querySelector(".alert")).not.toBeNull();
  });
});
