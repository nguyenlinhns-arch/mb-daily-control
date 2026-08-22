(() => {
  "use strict";

  const routeRequested = () => {
    const url = new URL(window.location.href);
    return url.searchParams.get("checkout") === "1"
      || url.hash === "#checkout"
      || url.hash === "#thanh-toan";
  };

  const clearRoute = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete("checkout");
    if (url.hash === "#checkout" || url.hash === "#thanh-toan") url.hash = "";
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}` || "/");
  };

  const openPaidCheckout = () => {
    if (!routeRequested()) return false;

    const button = Array.from(document.querySelectorAll("[data-open-checkout]"))
      .find((node) => !node.disabled && node.getAttribute("aria-disabled") !== "true");

    if (button) {
      clearRoute();
      button.click();
      return true;
    }

    const checkout = document.getElementById("checkout");
    if (checkout) {
      clearRoute();
      checkout.hidden = false;
      document.body.classList.add("modal-open", "checkout-open");
      document.getElementById("checkout-close")?.focus();
      return true;
    }

    return false;
  };

  const start = () => {
    if (openPaidCheckout()) return;
    window.setTimeout(openPaidCheckout, 250);
    window.setTimeout(openPaidCheckout, 900);
    window.setTimeout(openPaidCheckout, 1800);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
