(function () {
  const body = document.body;

  function cleanPath(path) {
    return path.replace(/\/+$/, "") || "/";
  }

  function setActiveLinks() {
    const currentPath = cleanPath(window.location.pathname);
    const links = document.querySelectorAll(".app-nav-link, .nav-links a");

    links.forEach((link) => {
      const href = link.getAttribute("href");
      if (!href || href.startsWith("http") || href.startsWith("#")) {
        return;
      }

      const linkPath = cleanPath(href);
      const isMatch =
        currentPath === linkPath ||
        (linkPath !== "/" && currentPath.startsWith(linkPath));

      if (isMatch) {
        link.classList.add("is-active");
      }
    });
  }

  function setupMobileNav() {
    const toggle = document.querySelector("[data-nav-toggle]");
    const menu = document.querySelector("[data-nav-menu]");
    if (!toggle || !menu) {
      return;
    }

    toggle.addEventListener("click", () => {
      menu.classList.toggle("open");
      const expanded = menu.classList.contains("open");
      toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
    });
  }

  function setupSidebar() {
    const sidebar = document.querySelector(".app-sidebar");
    const toggles = document.querySelectorAll("[data-sidebar-toggle]");
    if (!sidebar || !toggles.length) {
      return;
    }

    const storageKey = "online_exam_sidebar_collapsed";
    const desktop = () => window.matchMedia("(min-width: 901px)").matches;

    const stored = localStorage.getItem(storageKey);
    if (stored === "1" && desktop()) {
      body.classList.add("sidebar-collapsed");
    }

    toggles.forEach((toggle) => {
      toggle.addEventListener("click", () => {
        if (desktop()) {
          body.classList.toggle("sidebar-collapsed");
          localStorage.setItem(
            storageKey,
            body.classList.contains("sidebar-collapsed") ? "1" : "0"
          );
        } else {
          body.classList.toggle("sidebar-open");
        }
      });
    });

    document.addEventListener("click", (event) => {
      if (desktop() || !body.classList.contains("sidebar-open")) {
        return;
      }

      const clickedInsideSidebar = sidebar.contains(event.target);
      const clickedToggle = Array.from(toggles).some((btn) => btn.contains(event.target));
      if (!clickedInsideSidebar && !clickedToggle) {
        body.classList.remove("sidebar-open");
      }
    });

    window.addEventListener("resize", () => {
      if (desktop()) {
        body.classList.remove("sidebar-open");
      }
    });
  }

  function setupReveal() {
    const targets = document.querySelectorAll(
      ".hero-content, .hero-card, .auth-card, .form-card, .alert-card, .waiting-card, .card, .panel, .jumbotron, .table-card, .metric-card, form, table"
    );

    targets.forEach((el, index) => {
      if (!el.classList.contains("reveal")) {
        el.classList.add("reveal");
      }
      el.style.transitionDelay = `${Math.min(index * 45, 380)}ms`;
    });

    if (!("IntersectionObserver" in window)) {
      targets.forEach((el) => el.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );

    targets.forEach((el) => observer.observe(el));
  }

  function setupExamTimer() {
    const timerRoot = document.querySelector("[data-exam-timer]");
    const form = document.querySelector("[data-exam-form]");
    if (!timerRoot || !form) {
      return;
    }

    let secondsLeft = Number.parseInt(timerRoot.dataset.duration || "", 10);
    if (!Number.isFinite(secondsLeft) || secondsLeft <= 0) {
      return;
    }

    const display = timerRoot.querySelector("[data-exam-timer-display]");

    function format(seconds) {
      const minutes = Math.floor(seconds / 60)
        .toString()
        .padStart(2, "0");
      const secs = (seconds % 60).toString().padStart(2, "0");
      return `${minutes}:${secs}`;
    }

    function render() {
      if (display) {
        display.textContent = format(secondsLeft);
      }

      timerRoot.classList.remove("is-warning", "is-danger");
      if (secondsLeft <= 300) {
        timerRoot.classList.add("is-danger");
      } else if (secondsLeft <= 600) {
        timerRoot.classList.add("is-warning");
      }
    }

    render();

    const timerId = window.setInterval(() => {
      secondsLeft -= 1;
      render();

      if (secondsLeft <= 0) {
        window.clearInterval(timerId);
        form.submit();
      }
    }, 1000);

    form.addEventListener("submit", () => {
      window.clearInterval(timerId);
    });
  }

  function setupMathRendering() {
    if (!window.MathJax || typeof window.MathJax.typesetPromise !== "function") {
      return;
    }

    window.MathJax.typesetPromise().catch(() => {
      // Ignore rendering errors to avoid blocking UI interactions.
    });
  }

  setActiveLinks();
  setupMobileNav();
  setupSidebar();
  setupReveal();
  setupExamTimer();
  setupMathRendering();
})();
