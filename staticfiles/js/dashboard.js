/**
 * JanRakshak AI — Dashboard JS
 * Initializes Chart.js visualizations using data injected from the Django view.
 * Charts are rendered after GSAP page-enter animation completes.
 */

document.addEventListener("DOMContentLoaded", () => {
  if (typeof Chart === "undefined") {
    console.warn("[Dashboard] Chart.js not loaded. Charts will not render.");
    return;
  }

  // ---------------------------------------------------------------------------
  // Brand color palette (mirrors CSS custom properties for consistency)
  // ---------------------------------------------------------------------------
  const COLORS = {
    primary:   "#0E7490",
    secondary: "#164E63",
    accent:    "#06B6D4",
    critical:  "#DC2626",
    high:      "#EA580C",
    medium:    "#D97706",
    low:       "#16A34A",
    muted:     "#94A3B8",
    border:    "#E2E8F0",
    surface:   "#F8FAFC",
  };

  /** Map issue category names to deterministic brand-adjacent colors */
  const ISSUE_COLORS = [
    "#0E7490", "#06B6D4", "#0891B2", "#164E63",
    "#EA580C", "#D97706", "#16A34A", "#DC2626",
  ];

  const PRIORITY_COLORS = {
    Critical: COLORS.critical,
    High: COLORS.high,
    Medium: COLORS.medium,
    Low: COLORS.low,
    Unknown: COLORS.muted,
  };

  // ---------------------------------------------------------------------------
  // Chart.js global defaults — consistent typography and border radii
  // ---------------------------------------------------------------------------
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.font.size = 13;
  Chart.defaults.color = "#64748B";
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.legend.labels.padding = 16;
  Chart.defaults.plugins.tooltip.backgroundColor = "#0F172A";
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;

  // ---------------------------------------------------------------------------
  // 1. Issue Distribution — Donut Chart
  // ---------------------------------------------------------------------------

  const issueCanvas = document.getElementById("chart-issue-distribution");
  if (issueCanvas) {
    // Data is injected from Django view as a JSON blob in the template
    const issueData = JSON.parse(
      document.getElementById("issue-distribution-data")?.textContent || "[]"
    );

    if (issueData.length > 0) {
      new Chart(issueCanvas, {
        type: "doughnut",
        data: {
          labels: issueData.map((d) => d.label),
          datasets: [
            {
              data: issueData.map((d) => d.count),
              backgroundColor: ISSUE_COLORS.slice(0, issueData.length),
              borderColor: "#FFFFFF",
              borderWidth: 3,
              hoverOffset: 6,
            },
          ],
        },
        options: {
          cutout: "72%",
          responsive: true,
          maintainAspectRatio: false,
          animation: {
            animateRotate: true,
            duration: 800,
            easing: "easeOutQuart",
          },
          plugins: {
            legend: {
              position: "bottom",
              labels: { usePointStyle: true, pointStyle: "circle" },
            },
            tooltip: {
              callbacks: {
                label: (ctx) => ` ${ctx.label}: ${ctx.raw} reports`,
              },
            },
          },
        },
      });
    } else {
      issueCanvas.parentElement.innerHTML =
        `<p class="text-slate-400 text-sm text-center py-8">No data yet. Submit a report to populate this chart.</p>`;
    }
  }

  // ---------------------------------------------------------------------------
  // 2. Priority Distribution — Horizontal Bar Chart
  // ---------------------------------------------------------------------------

  const priorityCanvas = document.getElementById("chart-priority-distribution");
  if (priorityCanvas) {
    const priorityData = JSON.parse(
      document.getElementById("priority-distribution-data")?.textContent || "[]"
    );

    if (priorityData.length > 0) {
      new Chart(priorityCanvas, {
        type: "bar",
        data: {
          labels: priorityData.map((d) => d.label),
          datasets: [
            {
              label: "Reports",
              data: priorityData.map((d) => d.count),
              backgroundColor: priorityData.map(
                (d) => PRIORITY_COLORS[d.label] || COLORS.muted
              ),
              borderRadius: 6,
              borderSkipped: false,
              maxBarThickness: 40,
            },
          ],
        },
        options: {
          indexAxis: "y", // Horizontal bars
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 700, easing: "easeOutCubic" },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => ` ${ctx.raw} reports`,
              },
            },
          },
          scales: {
            x: {
              grid: { color: COLORS.border },
              ticks: { stepSize: 1, precision: 0 },
              border: { dash: [4, 4] },
            },
            y: {
              grid: { display: false },
            },
          },
        },
      });
    } else {
      priorityCanvas.parentElement.innerHTML =
        `<p class="text-slate-400 text-sm text-center py-8">No priority data yet.</p>`;
    }
  }


  // ---------------------------------------------------------------------------
  // 4. Real-time refresh button
  // ---------------------------------------------------------------------------

  const refreshBtn = document.getElementById("btn-refresh-dashboard");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      gsap.to(refreshBtn, {
        rotation: 360,
        duration: 0.6,
        ease: "power2.inOut",
        onComplete: () => {
          gsap.set(refreshBtn, { rotation: 0 });
          window.location.reload();
        },
      });
    });
  }
});
