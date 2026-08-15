(() => {
  "use strict";

  const url = new URL(window.location.href);
  const shouldOpen = url.searchParams.get("checkout") === "1" || window.location.hash === "#thanh-toan";
  if (!shouldOpen) return;

  let attempts = 0;
  const openCheckout = () => {
    attempts += 1;
    const button = [...document.querySelectorAll("[data-open-checkout]")]
      .find((node) => !node.disabled && node.getAttribute("aria-disabled") !== "true");
    if (button) {
      button.click();
      url.searchParams.delete("checkout");
      url.hash = "";
      window.history.replaceState({}, "", `${url.pathname}${url.search}`);
      return;
    }
    if (attempts < 20) window.setTimeout(openCheckout, 100);
  };

  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", openCheckout, { once: true });
  } else {
    openCheckout();
  }
})();
