import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { initConfirmDialogs } from "./confirm";

describe("confirm dialogs", () => {
  beforeEach(() => {
    document.body.replaceChildren();
    initConfirmDialogs();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls issueRequest when user confirms", () => {
    const button = document.createElement("button");
    button.setAttribute("data-confirm", "Are you sure?");
    document.body.appendChild(button);

    const issueRequest = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(true);

    const event = new CustomEvent("htmx:confirm", {
      bubbles: true,
      cancelable: true,
      detail: { issueRequest },
    });
    button.dispatchEvent(event);

    expect(window.confirm).toHaveBeenCalledWith("Are you sure?");
    expect(issueRequest).toHaveBeenCalledWith(true);
  });

  it("prevents request when user cancels", () => {
    const button = document.createElement("button");
    button.setAttribute("data-confirm", "Delete this?");
    document.body.appendChild(button);

    const issueRequest = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(false);

    const event = new CustomEvent("htmx:confirm", {
      bubbles: true,
      cancelable: true,
      detail: { issueRequest },
    });
    button.dispatchEvent(event);

    expect(window.confirm).toHaveBeenCalledWith("Delete this?");
    expect(issueRequest).not.toHaveBeenCalled();
  });

  it("does nothing for elements without data-confirm", () => {
    const button = document.createElement("button");
    document.body.appendChild(button);

    const issueRequest = vi.fn();
    vi.spyOn(window, "confirm");

    const event = new CustomEvent("htmx:confirm", {
      bubbles: true,
      cancelable: true,
      detail: { issueRequest },
    });
    button.dispatchEvent(event);

    expect(window.confirm).not.toHaveBeenCalled();
  });
});
