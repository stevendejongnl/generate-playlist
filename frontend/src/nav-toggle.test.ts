import { describe, it, expect, beforeEach } from "vitest";
import { initNavToggle } from "./nav-toggle";

function setUpHeader(): { toggle: HTMLButtonElement; nav: HTMLElement } {
  document.body.innerHTML = `
    <header class="app-header">
      <a href="/" class="logo">Playlist Generator</a>
      <button class="nav-toggle" aria-label="Menu" aria-expanded="false">☰</button>
      <nav>
        <a href="/base-list">Sources</a>
        <a href="/generate">Generate</a>
      </nav>
    </header>
  `;
  return {
    toggle: document.querySelector(".nav-toggle") as HTMLButtonElement,
    nav: document.querySelector(".app-header nav") as HTMLElement,
  };
}

describe("nav toggle", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("opens the nav on toggle click", () => {
    const { toggle, nav } = setUpHeader();
    initNavToggle();

    toggle.click();

    expect(nav.classList.contains("nav-open")).toBe(true);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(toggle.textContent).toBe("✕");
  });

  it("closes the nav on a second toggle click", () => {
    const { toggle, nav } = setUpHeader();
    initNavToggle();

    toggle.click();
    toggle.click();

    expect(nav.classList.contains("nav-open")).toBe(false);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(toggle.textContent).toBe("☰");
  });

  it("closes the nav when a link is clicked", () => {
    const { toggle, nav } = setUpHeader();
    initNavToggle();

    toggle.click();
    nav.querySelector("a")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(nav.classList.contains("nav-open")).toBe(false);
  });

  it("closes the nav on an outside click", () => {
    const { toggle, nav } = setUpHeader();
    initNavToggle();

    toggle.click();
    document.body.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(nav.classList.contains("nav-open")).toBe(false);
  });

  it("does nothing when the toggle or nav is missing", () => {
    document.body.innerHTML = "";
    expect(() => initNavToggle()).not.toThrow();
  });
});
