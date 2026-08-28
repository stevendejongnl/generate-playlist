/**
 * Toggle the header nav into a dropdown menu on small screens.
 */
export function initNavToggle(): void {
  const toggle = document.querySelector<HTMLButtonElement>(".nav-toggle");
  const nav = document.querySelector<HTMLElement>(".app-header nav");
  if (!toggle || !nav) return;

  const setOpen = (open: boolean): void => {
    nav.classList.toggle("nav-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "✕" : "☰";
  };

  toggle.addEventListener("click", () => {
    setOpen(!nav.classList.contains("nav-open"));
  });

  nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => setOpen(false));
  });

  document.addEventListener("click", (evt) => {
    const target = evt.target as Node;
    if (!nav.classList.contains("nav-open")) return;
    if (nav.contains(target) || toggle.contains(target)) return;
    setOpen(false);
  });
}
