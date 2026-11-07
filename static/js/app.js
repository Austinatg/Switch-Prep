document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const wrap = button.closest(".password-wrap");
      const input = wrap ? wrap.querySelector("input") : null;
      if (!input) return;
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      button.setAttribute("aria-pressed", String(!showing));
      button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
      button.setAttribute("title", showing ? "Show password" : "Hide password");
      button.classList.toggle("is-visible", !showing);
    });
  });
  document.querySelectorAll("[data-copy-code]").forEach((button) => {
    button.addEventListener("click", async () => {
      const code = button.closest(".code-example")?.querySelector("pre code")?.innerText || "";
      try {
        await navigator.clipboard.writeText(code);
        button.textContent = "Copied!";
        setTimeout(() => { button.textContent = "Copy"; }, 1400);
      } catch (error) {
        button.textContent = "Select code";
      }
    });
  });
  document.querySelectorAll("[data-quick-note-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      const feedback = form.querySelector("[data-note-feedback]");
      const noteList = document.querySelector("[data-note-list]");
      const noteCount = document.querySelector("[data-note-count]");
      const content = form.querySelector('[name="content"]');
      const importance = form.querySelector('[name="importance"]');
      const originalLabel = button.textContent;

      button.disabled = true;
      button.textContent = "Adding...";
      feedback.textContent = "";
      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        });
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.error || "Your note could not be saved.");
        }

        const emptyMessage = noteList.querySelector("[data-note-empty]");
        if (emptyMessage) emptyMessage.remove();
        const card = document.createElement("article");
        card.className = `note-point-card importance-${result.importance}`;
        const marker = document.createElement("div");
        marker.className = "note-point-marker";
        const body = document.createElement("div");
        body.className = "note-point-body";
        const pointContent = document.createElement("p");
        pointContent.textContent = result.content;
        const metadata = document.createElement("small");
        metadata.textContent = `Added ${result.created_at} · ${result.importance_label}`;
        body.append(pointContent, metadata);
        card.append(marker, body);
        noteList.prepend(card);
        noteCount.textContent = String(Number(noteCount.textContent) + 1);
        content.value = "";
        importance.value = "normal";
        feedback.textContent = "Note added to today’s daily notes.";
      } catch (error) {
        feedback.textContent = error.message || "Your note could not be saved. Please try again.";
      } finally {
        button.disabled = false;
        button.textContent = originalLabel;
      }
    });
  });
  const menu = document.getElementById("mobileMenu");
  const sidebar = document.getElementById("sidebar");
  if (menu && sidebar) menu.addEventListener("click", () => sidebar.classList.toggle("sidebar-open"));
});
