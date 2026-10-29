"use strict";

/* No telemetry, cookies, analytics, external requests or persistent user data. */
(() => {
  const progress = document.getElementById("reading-progress");
  const toast = document.getElementById("toast");
  const nav = document.querySelector(".rail-nav");
  const navMore = document.querySelector(".nav-more");
  function updateNavCue() {
    // Only a narrow-screen affordance; not a fake link to another page.
    const scrollable = nav.scrollWidth > nav.clientWidth + 3;
    navMore.hidden = !scrollable || nav.scrollLeft + nav.clientWidth >= nav.scrollWidth - 4;
  }
  navMore.addEventListener("click", () => {
    nav.scrollBy({ left: Math.max(135, nav.clientWidth * 0.7), behavior: "auto" });
    updateNavCue();
  });
  nav.addEventListener("scroll", updateNavCue, { passive: true });
  nav.addEventListener("focusin", updateNavCue);
  window.addEventListener("resize", updateNavCue);
  window.addEventListener("load", updateNavCue);
  updateNavCue();
  const navLinks = [...document.querySelectorAll(".rail-nav a")];
  const filters = [...document.querySelectorAll("[data-filter]")];
  const paperRows = [...document.querySelectorAll(".paper-row")];
  const empty = document.getElementById("empty-filter");
  const reportUrl = document.body.dataset.reportUrl;
  const edition = document.body.dataset.edition;

  let lastToast = null;
  function announce(message) {
    if (lastToast) window.clearTimeout(lastToast);
    toast.textContent = message;
    toast.classList.add("visible");
    lastToast = window.setTimeout(() => toast.classList.remove("visible"), 2800);
  }

  function updateProgress() {
    const total = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const value = Math.max(0, Math.min(100, Math.round(window.scrollY / total * 100)));
    progress.style.width = value + "%";
    progress.setAttribute("aria-valuenow", String(value));
  }
  window.addEventListener("scroll", updateProgress, { passive: true });
  window.addEventListener("resize", updateProgress);
  updateProgress();

  filters.forEach((button) => {
    button.addEventListener("click", () => {
      filters.forEach((other) => {
        const selected = other === button;
        other.classList.toggle("active", selected);
        other.setAttribute("aria-pressed", String(selected));
      });
      let shown = 0;
      paperRows.forEach((row) => {
        const match = button.dataset.filter === "all" || row.dataset.category === button.dataset.filter;
        row.hidden = !match;
        if (match) shown++;
      });
      empty.hidden = shown !== 0;
      updateProgress();
    });
  });

  if ("IntersectionObserver" in window) {
    const sections = [...document.querySelectorAll("section[id]")];
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        navLinks.forEach(link => link.classList.toggle("active", link.hash === "#" + entry.target.id));
      }
    }, { rootMargin: "-12% 0px -68% 0px", threshold: 0 });
    sections.forEach(section => observer.observe(section));
  }

  async function copyPrompt(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(text); return true; }
      catch (_) { /* use non-clipboard fallback */ }
    }
    // Some browsers deliberately restrict clipboard access from local previews.
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("aria-label", "Research prompt to copy");
    area.style.cssText = "position:fixed;left:0;top:0;opacity:.01;z-index:2000";
    document.body.appendChild(area);
    area.focus();
    area.select();
    let success = false;
    try { success = document.execCommand("copy"); }
    catch (_) { success = false; }
    area.remove();
    return success;
  }

  document.querySelectorAll("[data-copy-prompt]").forEach((button) => {
    button.addEventListener("click", async () => {
      const prompt = [
        "Explore this Quant Folio Research Briefing V1 paper using the pinned source:",
        reportUrl,
        "",
        "Paper: " + button.dataset.title,
        "arXiv: " + button.dataset.url,
        "Source ID: " + button.dataset.id,
        "",
        "Explain the paper's author-reported method, potential quantitative-research relevance and paper-specific limitations.",
        "Distinguish abstract-only author claims from independently verified findings.",
        "Do not infer profitability, execute inference, modify repositories or place trades."
      ].join("\n");
      const copied = await copyPrompt(prompt);
      if (copied) {
        button.focus();
        announce("Research prompt copied. Paste it into a ChatGPT conversation.");
      } else {
        const dialog = document.getElementById("prompt-dialog");
        document.getElementById("prompt-text").value = prompt;
        if (dialog.showModal) {
          dialog.addEventListener("close", () => button.focus(), { once: true });
          dialog.showModal();
        } else {
          button.focus();
          announce("Clipboard blocked; open the paper and pinned report links instead.");
        }
      }
    });
  });

  const date = new Date(edition + "T00:00:00Z");
  const today = new Date();
  const todayUTC = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  const age = Math.floor((todayUTC - date.getTime()) / 86400000);
  if (Number.isFinite(age) && age > 8) {
    const warning = document.createElement("span");
    warning.className = "age-warning";
    warning.textContent = "ARCHIVE · " + age + " DAYS OLD";
    warning.setAttribute("role", "status");
    document.querySelector(".topbar-right").appendChild(warning);
  }
})();
