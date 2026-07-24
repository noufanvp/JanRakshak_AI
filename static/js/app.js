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
// 2. TOP LOADER & SMOOTH PAGE TRANSITION SYSTEM
// ==========================================================================

function startTopLoader() {
  const loader = document.getElementById("top-loader");
  if (!loader) return;
  loader.classList.add("active");
  loader.style.width = "35%";
  setTimeout(() => {
    if (loader.classList.contains("active")) {
      loader.style.width = "75%";
    }
  }, 120);
}

function completeTopLoader() {
  const loader = document.getElementById("top-loader");
  if (!loader) return;
  loader.style.width = "100%";
  setTimeout(() => {
    loader.classList.remove("active");
    setTimeout(() => {
      loader.style.width = "0%";
    }, 200);
  }, 250);
}

/**
 * Runs once GSAP is available (loaded via CDN in base.html).
 * Creates a cinematic stagger fade-in for the page content.
 */
function initPageAnimations() {
  completeTopLoader();

  const mainContent = document.getElementById("main-content");
  if (mainContent) {
    mainContent.classList.remove("page-transitioning");
  }

  if (typeof gsap === "undefined") return;

  // Register ScrollTrigger plugin if available
  if (typeof ScrollTrigger !== "undefined") {
    gsap.registerPlugin(ScrollTrigger);
  }

  // ---------- Page-level enter animation ----------
  const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

  // Main content container fade in
  if (mainContent) {
    tl.from(mainContent, { opacity: 0, y: 10, duration: 0.35 });
  }

  // Hero / page header fades in
  tl.from(".page-header", { y: 18, opacity: 0, duration: 0.45 }, "-=0.2");

  // Metric cards stagger up
  tl.from(
    ".metric-card",
    { y: 24, opacity: 0, duration: 0.4, stagger: 0.06 },
    "-=0.25"
  );

  // Content panels stagger in
  tl.from(
    ".content-panel",
    { y: 18, opacity: 0, duration: 0.4, stagger: 0.05 },
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
        x: -12,
        opacity: 0,
        duration: 0.3,
        delay: i * 0.02,
        ease: "power2.out",
      });
    });
  }
}

// Attach smooth click handlers to page links
document.addEventListener("DOMContentLoaded", () => {
  initPageAnimations();

  document.addEventListener("click", (e) => {
    const link = e.target.closest("a");
    if (!link) return;

    const href = link.getAttribute("href");
    if (
      !href ||
      href.startsWith("#") ||
      href.startsWith("javascript:") ||
      href.startsWith("tel:") ||
      href.startsWith("mailto:") ||
      link.target === "_blank" ||
      e.ctrlKey ||
      e.metaKey ||
      e.shiftKey ||
      e.altKey
    ) {
      return;
    }

    try {
      const targetUrl = new URL(link.href, window.location.origin);
      if (targetUrl.origin === window.location.origin) {
        // If clicking the current exact page URL, skip full reload animation
        if (targetUrl.pathname === window.location.pathname && targetUrl.search === window.location.search) {
          return;
        }

        const mainContent = document.getElementById("main-content");
        startTopLoader();

        if (mainContent) {
          mainContent.classList.add("page-transitioning");
        }

        e.preventDefault();
        setTimeout(() => {
          window.location.href = link.href;
        }, 160);
      }
    } catch (err) {
      // Fallback normal navigation
    }
  });
});

// ==========================================================================
// 3. MOBILE NAV TOGGLE
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  const menuBtn = document.getElementById("mobile-menu-btn");
  const mobileMenu = document.getElementById("mobile-menu");
  const iconOpen = document.getElementById("menu-icon-open");
  const iconClose = document.getElementById("menu-icon-close");

  function openMenu() {
    mobileMenu.classList.remove("hidden");
    menuBtn.setAttribute("aria-expanded", "true");
    if (iconOpen) iconOpen.classList.add("hidden");
    if (iconClose) iconClose.classList.remove("hidden");
    if (typeof gsap !== "undefined") {
      gsap.from(mobileMenu, { height: 0, opacity: 0, duration: 0.28, ease: "power2.out" });
    }
  }

  function closeMenu() {
    mobileMenu.classList.add("hidden");
    menuBtn.setAttribute("aria-expanded", "false");
    if (iconOpen) iconOpen.classList.remove("hidden");
    if (iconClose) iconClose.classList.add("hidden");
  }

  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener("click", () => {
      const isHidden = mobileMenu.classList.contains("hidden");
      if (isHidden) {
        openMenu();
      } else {
        closeMenu();
      }
    });

    // Close on Escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !mobileMenu.classList.contains("hidden")) {
        closeMenu();
        menuBtn.focus();
      }
    });

    // Close on outside click
    document.addEventListener("click", (e) => {
      if (!menuBtn.contains(e.target) && !mobileMenu.contains(e.target)) {
        if (!mobileMenu.classList.contains("hidden")) {
          closeMenu();
        }
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
