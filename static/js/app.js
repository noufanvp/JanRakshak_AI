/**
 * JanRakshak AI — Shared Application JS
 * GSAP-powered page transitions, nav interactions, and shared utilities.
 * Loaded on every page via base.html.
 */

// ==========================================================================
// 1. SERVICE WORKER REGISTRATION
// ==========================================================================

if ("serviceWorker" in navigator) {
  window.addEventListener("load", async () => {
    try {
      const reg = await navigator.serviceWorker.register(
        "/serviceworker.js",
        { scope: "/" }
      );
      console.log("[PWA] Service Worker registered:", reg.scope);

      // Listen for updates to prompt the user to refresh
      reg.addEventListener("updatefound", () => {
        const newWorker = reg.installing;
        newWorker.addEventListener("statechange", () => {
          if (
            newWorker.state === "installed" &&
            navigator.serviceWorker.controller
          ) {
            JR.toast("App updated. Refresh for the latest version.", "info");
          }
        });
      });
    } catch (err) {
      console.warn("[PWA] Service Worker registration failed:", err);
    }
  });
}

// ==========================================================================
// 2. GSAP PAGE-ENTER ANIMATION
// ==========================================================================

/**
 * Runs once GSAP is available (loaded via CDN in base.html).
 * Creates a cinematic stagger fade-in for the page content.
 */
function initPageAnimations() {
  if (typeof gsap === "undefined") return;

  // Register ScrollTrigger plugin if available
  if (typeof ScrollTrigger !== "undefined") {
    gsap.registerPlugin(ScrollTrigger);
  }

  // ---------- Page-level enter animation ----------
  const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

  // Navbar slides down from above
  tl.from("#main-nav", { y: -60, opacity: 0, duration: 0.5 });

  // Hero / page header fades in
  tl.from(".page-header", { y: 24, opacity: 0, duration: 0.55 }, "-=0.2");

  // Metric cards stagger up
  tl.from(
    ".metric-card",
    { y: 32, opacity: 0, duration: 0.5, stagger: 0.08 },
    "-=0.3"
  );

  // Content panels stagger in
  tl.from(
    ".content-panel",
    { y: 24, opacity: 0, duration: 0.45, stagger: 0.06 },
    "-=0.2"
  );

  // ---------- Scroll-triggered animations for table rows ----------
  if (typeof ScrollTrigger !== "undefined") {
    gsap.utils.toArray(".data-row").forEach((row, i) => {
      gsap.from(row, {
        scrollTrigger: {
          trigger: row,
          start: "top 92%",
          toggleActions: "play none none none",
        },
        x: -16,
        opacity: 0,
        duration: 0.35,
        delay: i * 0.02,
        ease: "power2.out",
      });
    });
  }
}

// Run after DOM + GSAP are ready
document.addEventListener("DOMContentLoaded", initPageAnimations);

// ==========================================================================
// 3. MOBILE NAV TOGGLE
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  const menuBtn = document.getElementById("mobile-menu-btn");
  const mobileMenu = document.getElementById("mobile-menu");

  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener("click", () => {
      const isOpen = mobileMenu.classList.toggle("hidden");

      if (typeof gsap !== "undefined" && !isOpen) {
        gsap.from(mobileMenu, {
          height: 0,
          opacity: 0,
          duration: 0.28,
          ease: "power2.out",
        });
      }
    });
  }
});

// ==========================================================================
// 4. TOAST NOTIFICATION SYSTEM
// ==========================================================================

const JR = (() => {
  let _container = null;

  function _getContainer() {
    if (!_container) {
      _container = document.createElement("div");
      _container.id = "jr-toast-container";
      _container.className =
        "fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none";
      document.body.appendChild(_container);
    }
    return _container;
  }

  /**
   * Display a toast notification.
   * @param {string} message
   * @param {"success"|"error"|"warning"|"info"} type
   * @param {number} duration  milliseconds before auto-dismiss
   */
  function toast(message, type = "info", duration = 4000) {
    const colorMap = {
      success: "bg-green-600",
      error: "bg-red-600",
      warning: "bg-amber-500",
      info: "bg-cyan-700",
    };
    const iconMap = {
      success: "✓",
      error: "✕",
      warning: "⚠",
      info: "ℹ",
    };

    const el = document.createElement("div");
    el.className = `pointer-events-auto flex items-center gap-3 px-4 py-3
      rounded-lg shadow-lg text-white text-sm font-medium
      ${colorMap[type] || colorMap.info}`;
    el.innerHTML = `
      <span class="text-base">${iconMap[type] || "ℹ"}</span>
      <span>${message}</span>
    `;

    _getContainer().appendChild(el);

    // GSAP slide-in
    if (typeof gsap !== "undefined") {
      gsap.from(el, { x: 80, opacity: 0, duration: 0.3, ease: "power2.out" });
      gsap.to(el, {
        x: 80,
        opacity: 0,
        duration: 0.3,
        delay: duration / 1000,
        ease: "power2.in",
        onComplete: () => el.remove(),
      });
    } else {
      setTimeout(() => el.remove(), duration);
    }
  }

  return { toast };
})();

// Expose globally so inline scripts and other modules can call JR.toast()
window.JR = JR;

// ==========================================================================
// 5. PRIORITY BADGE COLOR HELPER
// ==========================================================================

/**
 * Returns a Tailwind class string for a priority level badge.
 * Used by dynamically-rendered table rows.
 */
function priorityClasses(priority) {
  const map = {
    Critical: "bg-red-100 text-red-700 border border-red-200",
    High: "bg-orange-100 text-orange-700 border border-orange-200",
    Medium: "bg-amber-100 text-amber-700 border border-amber-200",
    Low: "bg-green-100 text-green-700 border border-green-200",
    Unknown: "bg-slate-100 text-slate-600 border border-slate-200",
  };
  return map[priority] || map.Unknown;
}

window.priorityClasses = priorityClasses;
