(() => {
  "use strict";

  const shouldOpen = () => {
    const url = new URL(window.location.href);
    return url.searchParams.get("checkout") === "1" || url.hash === "#checkout";
  };

  const clearRoute = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete("checkout");
    if (url.hash === "#checkout") url.hash = "";
    const next = `${url.pathname}${url.search}${url.hash}` || "/";
    window.history.replaceState({}, "", next);
  };

  const openCheckout = () => {
    if (!shouldOpen()) return;
    const button = [...document.querySelectorAll("[data-open-checkout]")]
      .find((item) => !item.disabled && item.getAttribute("aria-disabled") !== "true");
    if (!button) return;
    clearRoute();
    window.setTimeout(() => button.click(), 30);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", openCheckout, { once: true });
  } else {
    openCheckout();
  }
})();
