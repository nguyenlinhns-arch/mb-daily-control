(() => {
  "use strict";

  const ZALO_URL = "https://zalo.me/0398696879";
  const url = new URL(window.location.href);
  const shouldRoute = url.searchParams.get("checkout") === "1" || window.location.hash === "#thanh-toan";
  if (!shouldRoute) return;

  url.searchParams.delete("checkout");
  url.hash = "";
  window.history.replaceState({}, "", `${url.pathname}${url.search}`);
  window.location.replace(ZALO_URL);
})();
