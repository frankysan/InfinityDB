/** Explicit feedback only; no browser state, query strings or fragments collected. */
export function initFeedback() {
  const footer = document.querySelector("main#main .page-footer");
  const dialog = footer?.querySelector(".feedback-dialog");
  if (!dialog || dialog.dataset.initialized) return;
  dialog.dataset.initialized = "true";
  const form = dialog.querySelector("form");
  const category = dialog.querySelector("#feedback-category");
  const message = dialog.querySelector("#feedback-message");
  const includePage = dialog.querySelector("#feedback-include-page");
  const context = dialog.querySelector("#feedback-context");
  const website = dialog.querySelector("#feedback-website");
  const status = dialog.querySelector("#feedback-status");
  const close = dialog.querySelector("#feedback-close");
  const submit = dialog.querySelector("#feedback-submit");
  let page = "";
  let sending = false;
  let sent = false;
  function preview() {
    const version = footer.querySelector(".version")?.textContent || "";
    context.textContent = (includePage.checked ? page : "Page not included") + " · " + version;
  }
  includePage.addEventListener("change", preview);
  for (const button of footer.querySelectorAll(".feedback-open")) {
    button.hidden = false;
    button.addEventListener("click", async () => {
      if (sending) return;
      page = location.pathname;
      if (sent) {
        form.reset();
        sent = false;
      }
      status.textContent = "";
      close.textContent = "Cancel";
      submit.disabled = true;
      message.disabled = category.disabled = includePage.disabled = false;
      preview();
      dialog.showModal();
      message.focus();
      status.textContent = "Checking reporting availability…";
      try {
        const response = await fetch("/api/feedback", {
          credentials: "omit", referrerPolicy: "origin", cache: "no-store",
        });
        const available = response.ok && (await response.json()).enabled === true;
        submit.disabled = !available;
        status.textContent = available ? "" : "Reporting is currently unavailable.";
      } catch {
        status.textContent = "Could not check reporting availability.";
      }
    });
  }
  close.addEventListener("click", () => dialog.close());
  dialog.addEventListener("cancel", (event) => {
    if (sending) event.preventDefault();
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (sending || sent) return;
    const text = message.value.trim();
    if (!text) {
      status.textContent = "Please describe the problem.";
      message.focus();
      return;
    }
    const payload = {
      category: category.value,
      message: text,
      page: includePage.checked ? page : "",
      website: website.value,
    };
    sending = true;
    submit.disabled = close.disabled = true;
    message.disabled = category.disabled = includePage.disabled = true;
    status.textContent = "Sending report…";
    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
        credentials: "omit",
        referrerPolicy: "origin",
        cache: "no-store",
      });
      if (response.status === 202) {
        sent = true;
        status.textContent = "Report received. Thank you.";
        close.textContent = "Close";
        message.value = "";
      } else {
        status.textContent = response.status === 429
          ? "Too many reports right now. Try again in a minute."
          : "Could not send the report. Check the context or try again.";
      }
    } catch {
      status.textContent = "Could not send the report. Check your connection and try again.";
    } finally {
      sending = false;
      close.disabled = false;
      submit.disabled = sent;
      message.disabled = category.disabled = includePage.disabled = sent;
      if (sent) close.focus();
    }
  });
}
