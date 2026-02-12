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

  function setupFacultyDepartmentFields() {
    const facultySelects = document.querySelectorAll("select[data-department-map]");
    if (!facultySelects.length) {
      return;
    }

    facultySelects.forEach((facultySelect) => {
      const form = facultySelect.closest("form");
      const departmentSelect = form
        ? form.querySelector("select[name='department']")
        : null;
      if (!departmentSelect) {
        return;
      }

      let departmentMap = {};
      try {
        departmentMap = JSON.parse(facultySelect.dataset.departmentMap || "{}");
      } catch (_err) {
        departmentMap = {};
      }

      const rebuildDepartments = () => {
        const facultyValue = facultySelect.value;
        if (!facultyValue) {
          departmentSelect.innerHTML = "";
          const emptyOption = document.createElement("option");
          emptyOption.value = "";
          emptyOption.textContent = "Select Faculty First";
          departmentSelect.appendChild(emptyOption);
          return;
        }

        if (!Object.prototype.hasOwnProperty.call(departmentMap, facultyValue)) {
          return;
        }

        const departments = departmentMap[facultyValue] || [];
        const existingSelection = departmentSelect.value;

        departmentSelect.innerHTML = "";
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Select Department";
        departmentSelect.appendChild(placeholder);

        departments.forEach((departmentName) => {
          const option = document.createElement("option");
          option.value = departmentName;
          option.textContent = departmentName;
          departmentSelect.appendChild(option);
        });

        if (existingSelection && departments.includes(existingSelection)) {
          departmentSelect.value = existingSelection;
        }
      };

      facultySelect.addEventListener("change", rebuildDepartments);
      rebuildDepartments();
    });
  }

  function setupMetricCounters() {
    const values = document.querySelectorAll(".metric-value span");
    if (!values.length) {
      return;
    }

    const parseTarget = (rawText) => {
      const text = (rawText || "").trim();
      if (!text) {
        return null;
      }

      const hasPercent = text.endsWith("%");
      const numericPart = hasPercent ? text.slice(0, -1) : text;
      const normalized = numericPart.replace(/,/g, "");
      if (!/^\d+(\.\d+)?$/.test(normalized)) {
        return null;
      }

      const target = Number.parseFloat(normalized);
      if (!Number.isFinite(target)) {
        return null;
      }

      const decimals = normalized.includes(".")
        ? normalized.split(".")[1].length
        : 0;
      return { target, decimals, suffix: hasPercent ? "%" : "" };
    };

    const formatValue = (value, decimals, suffix) => {
      if (decimals > 0) {
        return `${value.toLocaleString(undefined, {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        })}${suffix}`;
      }
      return `${Math.round(value).toLocaleString()}${suffix}`;
    };

    const animateCounter = (el, targetConfig) => {
      const { target, decimals, suffix } = targetConfig;
      const duration = 880;
      const start = performance.now();

      const step = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = target * eased;

        el.textContent = formatValue(current, decimals, suffix);
        if (progress < 1) {
          window.requestAnimationFrame(step);
        } else {
          el.textContent = formatValue(target, decimals, suffix);
        }
      };

      window.requestAnimationFrame(step);
    };

    if (!("IntersectionObserver" in window)) {
      values.forEach((el) => {
        const config = parseTarget(el.textContent);
        if (config) {
          animateCounter(el, config);
        }
      });
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }

          const config = parseTarget(entry.target.textContent);
          if (config) {
            animateCounter(entry.target, config);
          }
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.45 }
    );

    values.forEach((el) => observer.observe(el));
  }

  function setupTableRowMotion() {
    const rows = document.querySelectorAll(".table tbody tr");
    if (!rows.length) {
      return;
    }

    rows.forEach((row, index) => {
      row.classList.add("table-row-entrance");
      row.style.animationDelay = `${Math.min(index * 38, 300)}ms`;
    });
  }

  function setupButtonRipples() {
    const controls = document.querySelectorAll(".btn, button, input[type='submit']");
    if (!controls.length) {
      return;
    }

    controls.forEach((control) => {
      control.addEventListener("pointerdown", (event) => {
        if (control.disabled || control.tagName === "INPUT") {
          return;
        }

        const rect = control.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height) * 1.25;
        const ripple = document.createElement("span");
        ripple.className = "btn-ripple";
        ripple.style.width = `${size}px`;
        ripple.style.height = `${size}px`;
        ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
        ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
        control.appendChild(ripple);

        ripple.addEventListener("animationend", () => ripple.remove(), { once: true });
      });
    });
  }

  setActiveLinks();
  setupMobileNav();
  setupSidebar();
  setupReveal();
  setupExamTimer();
  setupMathRendering();
  setupFacultyDepartmentFields();
  setupMetricCounters();
  setupTableRowMotion();
  setupButtonRipples();
})();
