(() => {
  const root = document.documentElement;
  const themeKey = "taskflow-theme";
  const savedTheme = localStorage.getItem(themeKey);
  if (savedTheme) root.dataset.theme = savedTheme;

  const updateThemeIcon = () => {
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      const icon = button.querySelector("i");
      if (icon) icon.className = root.dataset.theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
    });
  };
  updateThemeIcon();
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => button.addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem(themeKey, root.dataset.theme);
    updateThemeIcon();
    renderCharts();
  }));

  document.querySelectorAll("[data-confirm]").forEach((form) => form.addEventListener("submit", (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  }));

  document.querySelectorAll("[data-validate]").forEach((form) => form.addEventListener("submit", (event) => {
    let valid = true;
    form.querySelectorAll("[required]").forEach((input) => {
      const field = input.closest(".field");
      const error = field?.querySelector(".field-error");
      if (!input.value.trim()) {
        valid = false;
        field?.classList.add("invalid");
        if (error) error.textContent = "This field is required.";
      } else {
        field?.classList.remove("invalid");
        if (error) error.textContent = "";
      }
    });
    if (!valid) event.preventDefault();
  }));

  function renderCharts() {
    if (!window.taskflowStats || typeof Chart === "undefined") return;
    const stats = window.taskflowStats;
    const ink = getComputedStyle(root).getPropertyValue("--muted").trim();
    const primary = getComputedStyle(root).getPropertyValue("--primary").trim();
    const amber = getComputedStyle(root).getPropertyValue("--amber").trim();
    const red = getComputedStyle(root).getPropertyValue("--red").trim();
    const chartDefaults = { color: ink, font: { family: "DM Sans", size: 11 } };
    ["completionChart", "categoryChart", "priorityChart"].forEach((id) => {
      const canvas = document.getElementById(id);
      if (canvas) {
        const existing = Chart.getChart(canvas);
        if (existing) existing.destroy();
      }
    });
    const completion = document.getElementById("completionChart");
    if (completion) new Chart(completion, { type: "doughnut", data: { labels: ["Completed", "Pending"], datasets: [{ data: [stats.completed, stats.pending], backgroundColor: [primary, "#d8e0df"], borderWidth: 0 }] }, options: { responsive: true, cutout: "72%", plugins: { legend: { display: false } } } });
    const category = document.getElementById("categoryChart");
    if (category) new Chart(category, { type: "bar", data: { labels: stats.categories.map((item) => item.label), datasets: [{ data: stats.categories.map((item) => item.count), backgroundColor: primary, borderRadius: 4, barThickness: 14 }] }, options: { responsive: true, scales: { x: { ticks: chartDefaults, grid: { display: false } }, y: { ticks: chartDefaults, beginAtZero: true, grid: { color: "rgba(120,140,140,.12)" } } }, plugins: { legend: { display: false } } } });
    const priority = document.getElementById("priorityChart");
    if (priority) new Chart(priority, { type: "polarArea", data: { labels: stats.priorities.map((item) => item.label), datasets: [{ data: stats.priorities.map((item) => item.count), backgroundColor: [red, amber, primary], borderWidth: 2, borderColor: getComputedStyle(root).getPropertyValue("--surface").trim() }] }, options: { responsive: true, scales: { r: { ticks: { display: false }, grid: { color: "rgba(120,140,140,.16)" } } }, plugins: { legend: { position: "bottom", labels: chartDefaults } } } });
  }
  renderCharts();
})();
