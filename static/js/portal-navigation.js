document.addEventListener("DOMContentLoaded", () => {
  const layout = document.querySelector(".portal-layout");
  const menuToggle = document.querySelector(".menu-toggle");
  const scrim = document.querySelector(".sidebar-scrim");
  const sidebar = document.querySelector("#portal-sidebar");
  const backButton = document.querySelector("[data-back-button]");

  if (layout && menuToggle && scrim && sidebar) {
    const closeSidebar = () => {
      layout.classList.remove("sidebar-open");
      menuToggle.setAttribute("aria-expanded", "false");
      menuToggle.setAttribute("aria-label", "Open navigation");
    };

    menuToggle.addEventListener("click", () => {
      const isOpen = layout.classList.toggle("sidebar-open");
      menuToggle.setAttribute("aria-expanded", String(isOpen));
      menuToggle.setAttribute(
        "aria-label",
        isOpen ? "Close navigation" : "Open navigation",
      );
    });

    scrim.addEventListener("click", closeSidebar);
    sidebar.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", closeSidebar);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeSidebar();
    });
  }

  if (backButton) {
    backButton.addEventListener("click", (event) => {
      const referrer = document.referrer;
      if (!referrer) return;

      try {
        const previousPage = new URL(referrer);
        if (
          previousPage.origin === window.location.origin &&
          previousPage.href !== window.location.href &&
          window.history.length > 1
        ) {
          event.preventDefault();
          window.history.back();
        }
      } catch {
        // Keep the dashboard link as a safe fallback for invalid referrers.
      }
    });
  }
});
