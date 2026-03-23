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
    const totalDuration = secondsLeft;
    if (!Number.isFinite(secondsLeft) || secondsLeft <= 0) {
      return;
    }

    const display = timerRoot.querySelector("[data-exam-timer-display]");
    const progressFill = timerRoot.querySelector("[data-exam-timer-progress]");

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

      if (progressFill) {
        const percentage = (secondsLeft / totalDuration) * 100;
        progressFill.style.width = `${percentage}%`;
      }

      timerRoot.classList.remove("is-warning", "is-danger", "is-emergency", "is-pulsing");
      if (secondsLeft <= 60) {
        timerRoot.classList.add("is-danger", "is-emergency", "is-pulsing");
      } else if (secondsLeft <= 300) {
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

  function setupAutoSave() {
    const form = document.querySelector("[data-exam-form]");
    const savedDataEl = document.getElementById("saved-answers-data");
    if (!form || !savedDataEl) {
      return;
    }

    const courseId = form.querySelector('[name="course_id"]')?.value;
    if (!courseId) {
      return;
    }

    let savedAnswers = {};
    try {
      savedAnswers = JSON.parse(savedDataEl.textContent || "{}");
    } catch (e) {
      console.warn("Failed to parse saved answers:", e);
    }

    // Populate existing answers
    Object.entries(savedAnswers).forEach(([qId, value]) => {
      const radio = form.querySelector(`input[name="question_${qId}"][value="${value}"]`);
      if (radio) {
        radio.checked = true;
      } else {
        const textInput = form.querySelector(`input[name="question_${qId}"][data-short-answer]`);
        if (textInput) {
          textInput.value = value;
        }
      }
    });

    const getCookie = (name) => {
      let cookieValue = null;
      if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === name + "=") {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    };

    const csrftoken = getCookie("csrftoken");

    const saveAnswer = (questionId, value) => {
      fetch("/student/ajax-save-answer", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken,
        },
        body: JSON.stringify({
          course_id: courseId,
          question_id: questionId,
          option: value,
        }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.status !== "success") {
            console.error("Auto-save failed:", data);
          }
        })
        .catch((err) => console.error("Auto-save error:", err));
    };

    form.addEventListener("change", (event) => {
      const target = event.target;
      if (target.type === "radio" && target.name.startsWith("question_")) {
        const questionId = target.name.replace("question_", "");
        saveAnswer(questionId, target.value);
      }
    });

    const shortAnswers = form.querySelectorAll("[data-short-answer]");
    shortAnswers.forEach((input) => {
      let timeout = null;
      input.addEventListener("input", () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          const questionId = input.name.replace("question_", "");
          saveAnswer(questionId, input.value);
        }, 1000);
      });
    });
  }

  function setupAdminCharts() {
    const dataEl = document.getElementById("admin-charts-data");
    if (!dataEl) {
      return;
    }

    let chartsData = {};
    try {
      chartsData = JSON.parse(dataEl.textContent || "{}");
    } catch (e) {
      console.warn("Failed to parse admin charts data:", e);
      return;
    }

    // Pie Chart: Pass/Fail Distribution
    const pfCtx = document.getElementById("passFailChart")?.getContext("2d");
    if (pfCtx) {
      new window.Chart(pfCtx, {
        type: "doughnut",
        data: {
          labels: ["Pass", "Fail"],
          datasets: [
            {
              data: chartsData.pass_fail,
              backgroundColor: ["#48c9b0", "#ec7063"],
              borderWidth: 0,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "bottom" },
          },
          cutout: "70%",
        },
      });
    }

    // Bar Chart: Top Courses Pass Rate
    const tcCtx = document.getElementById("topCoursesChart")?.getContext("2d");
    if (tcCtx && chartsData.top_courses) {
      new window.Chart(tcCtx, {
        type: "bar",
        data: {
          labels: chartsData.top_courses.labels,
          datasets: [
            {
              label: "Pass Rate (%)",
              data: chartsData.top_courses.rates,
              backgroundColor: "#5dade2",
              borderRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
            },
          },
          plugins: {
            legend: { display: false },
          },
        },
      });
    }
  }

  function setupStudentCharts() {
    const dataEl = document.getElementById("student-performance-data");
    if (!dataEl) {
      return;
    }

    let perfData = {};
    try {
      perfData = JSON.parse(dataEl.textContent || "{}");
    } catch (e) {
      console.warn("Failed to parse student performance data:", e);
      return;
    }

    const ctx = document.getElementById("studentPerformanceChart")?.getContext("2d");
    if (ctx && perfData.labels && perfData.labels.length > 0) {
      new window.Chart(ctx, {
        type: "line",
        data: {
          labels: perfData.labels,
          datasets: [
            {
              label: "Score (%)",
              data: perfData.series,
              borderColor: "#5dade2",
              backgroundColor: "rgba(93, 173, 226, 0.1)",
              fill: true,
              tension: 0.4,
              pointRadius: 4,
              pointBackgroundColor: "#5dade2",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              ticks: {
                callback: (value) => value + "%",
              },
            },
          },
          plugins: {
            legend: { display: false },
          },
        },
      });
    }
  }

  function setupTeacherCharts() {
    const dataEl = document.getElementById("teacher-charts-data");
    if (!dataEl) {
      return;
    }

    let chartsData = {};
    try {
      chartsData = JSON.parse(dataEl.textContent || "{}");
    } catch (e) {
      console.warn("Failed to parse teacher charts data:", e);
      return;
    }

    const ctx = document.getElementById("teacherQuestionChart")?.getContext("2d");
    if (ctx && chartsData.labels && chartsData.labels.length > 0) {
      new window.Chart(ctx, {
        type: "bar",
        data: {
          labels: chartsData.labels,
          datasets: [
            {
              label: "Question Count",
              data: chartsData.counts,
              backgroundColor: "#48c9b0",
              borderRadius: 4,
            },
          ],
        },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
          },
          scales: {
            x: {
              beginAtZero: true,
              ticks: { stepSize: 1 },
            },
          },
        },
      });
    }
  }

  function setupMathRendering() {
    if (!window.MathJax || typeof window.MathJax.typesetPromise !== "function") {
      return;
    }

    window.MathJax.typesetPromise().catch(() => {
      // Ignore rendering errors to avoid blocking UI interactions.
    });
  }

  function setupConfirmationModals() {
    document.addEventListener("click", (e) => {
      const target = e.target.closest("[data-confirm]");
      if (target) {
        e.preventDefault();
        const message = target.getAttribute("data-confirm") || "Are you sure?";
        const url = target.getAttribute("href");

        showCustomConfirm(message, () => {
          window.location.href = url;
        });
      }
    });

    function showCustomConfirm(message, onConfirm) {
      const overlay = document.createElement("div");
      overlay.className = "custom-modal-overlay";
      overlay.innerHTML = `
        <div class="custom-modal">
          <div class="custom-modal-icon"><i class="fas fa-exclamation-triangle"></i></div>
          <div class="custom-modal-content">
            <h3>Confirm Action</h3>
            <p>${message}</p>
          </div>
          <div class="custom-modal-actions">
            <button class="btn btn-secondary btn-sm" data-modal-cancel>Cancel</button>
            <button class="btn btn-danger btn-sm" data-modal-confirm>Confirm</button>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);
      document.body.style.overflow = "hidden";

      const close = () => {
        overlay.classList.add("is-closing");
        setTimeout(() => {
          overlay.remove();
          document.body.style.overflow = "";
        }, 300);
      };

      overlay.addEventListener("click", (e) => {
        if (e.target === overlay || e.target.closest("[data-modal-cancel]")) {
          close();
        } else if (e.target.closest("[data-modal-confirm]")) {
          onConfirm();
          close();
        }
      });

      document.addEventListener(
        "keydown",
        (e) => {
          if (e.key === "Escape") close();
        },
        { once: true }
      );
    }
  }

  setActiveLinks();
  setupMobileNav();
  setupSidebar();
  setupReveal();
  setupExamTimer();
  setupAutoSave();
  setupAdminCharts();
  setupStudentCharts();
  setupTeacherCharts();
  setupMathRendering();
  setupConfirmationModals();
})();
