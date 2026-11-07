document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-ai-loading-form]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
        event.preventDefault();
        return;
      }
      const button = event.submitter || form.querySelector('button[type="submit"]');
      if (!button) return;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      if (button.classList.contains("ai-button")) {
        button.dataset.originalText = button.textContent;
        button.textContent = "Working...";
      }
    });
  });

  document.querySelectorAll("[data-copy-answer]").forEach((button) => {
    button.addEventListener("click", async () => {
      const content = document.querySelector("[data-answer-content]");
      if (!content) return;
      try {
        await navigator.clipboard.writeText(content.innerText);
        button.textContent = "Copied";
      } catch {
        button.textContent = "Copy unavailable";
      }
      window.setTimeout(() => { button.textContent = "Copy response"; }, 1400);
    });
  });

  document.querySelectorAll("[data-ai-clear]").forEach((button) => {
    button.addEventListener("click", () => {
      const form = button.closest("form");
      if (form) form.reset();
    });
  });

  const messages = document.querySelector("[data-chat-messages]");
  if (messages) messages.scrollTop = messages.scrollHeight;
});
