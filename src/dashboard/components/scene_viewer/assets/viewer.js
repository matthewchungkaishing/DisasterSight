(function () {
  "use strict";

  const MIN_SCALE = 1;
  const MAX_SCALE = 4;
  const ZOOM_STEP = 0.25;

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

  function readNumber(value, fallback) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
  }

  class PaneViewport {
    constructor(root, viewer) {
      this.root = root;
      this.viewer = viewer;
      this.viewport = root.querySelector(".pane-viewport");
      this.layer = root.querySelector(".pane-layer");
      this.image = root.querySelector("img");
      this.paneKey = root.dataset.pane || "";
      this.aspectWidth = readNumber(root.dataset.aspectWidth, 1);
      this.aspectHeight = readNumber(root.dataset.aspectHeight, 1);
      this.scale = 1;
      this.panX = 0;
      this.panY = 0;
      this.fitWidth = 0;
      this.fitHeight = 0;
      this.baseX = 0;
      this.baseY = 0;
      this.dragging = false;
      this.lastPointer = { x: 0, y: 0 };
      this._bindControls();
      this._bindPointer();
    }

    viewMode() {
      if (this.viewer.classList.contains("scene-viewer--solo-pre")) {
        return "solo-pre";
      }
      if (this.viewer.classList.contains("scene-viewer--solo-post")) {
        return "solo-post";
      }
      return "split";
    }

    alignment() {
      const mode = this.viewMode();
      if (mode === "solo-pre" || mode === "solo-post") {
        return "center";
      }
      if (this.paneKey === "pre") {
        return "end";
      }
      if (this.paneKey === "post") {
        return "start";
      }
      return "center";
    }

    measure() {
      const viewportWidth = this.viewport.clientWidth;
      const viewportHeight = this.viewport.clientHeight;
      if (!viewportWidth || !viewportHeight) {
        return;
      }

      let fitWidth = viewportWidth;
      let fitHeight = (fitWidth * this.aspectHeight) / this.aspectWidth;
      if (fitHeight > viewportHeight) {
        fitHeight = viewportHeight;
        fitWidth = (fitHeight * this.aspectWidth) / this.aspectHeight;
      }

      this.fitWidth = fitWidth;
      this.fitHeight = fitHeight;
      this.layer.style.width = `${fitWidth}px`;
      this.layer.style.height = `${fitHeight}px`;

      const align = this.alignment();
      if (align === "end") {
        this.baseX = viewportWidth - fitWidth;
      } else if (align === "start") {
        this.baseX = 0;
      } else {
        this.baseX = (viewportWidth - fitWidth) / 2;
      }
      this.baseY = (viewportHeight - fitHeight) / 2;

      this.clampPan();
      this.applyTransform();
    }

    applyTransform() {
      const x = this.baseX + this.panX;
      const y = this.baseY + this.panY;
      this.layer.style.transform = `translate(${x}px, ${y}px) scale(${this.scale})`;
      this.layer.style.transformOrigin = "0 0";
    }

    clampPan() {
      const scaledWidth = this.fitWidth * this.scale;
      const scaledHeight = this.fitHeight * this.scale;
      const viewportWidth = this.viewport.clientWidth;
      const viewportHeight = this.viewport.clientHeight;

      const minPanX =
        scaledWidth <= viewportWidth
          ? 0
          : viewportWidth - scaledWidth - this.baseX;
      const maxPanX = scaledWidth <= viewportWidth ? 0 : -this.baseX;
      const minPanY =
        scaledHeight <= viewportHeight
          ? 0
          : viewportHeight - scaledHeight - this.baseY;
      const maxPanY = scaledHeight <= viewportHeight ? 0 : -this.baseY;

      this.panX = clamp(this.panX, minPanX, maxPanX);
      this.panY = clamp(this.panY, minPanY, maxPanY);
    }

    resetView() {
      this.scale = 1;
      this.panX = 0;
      this.panY = 0;
      this.measure();
    }

    setScale(nextScale, focalX, focalY) {
      const clamped = clamp(nextScale, MIN_SCALE, MAX_SCALE);
      if (clamped === this.scale) {
        return;
      }

      const ratio = clamped / this.scale;
      const imageX = (focalX - this.baseX - this.panX) / this.scale;
      const imageY = (focalY - this.baseY - this.panY) / this.scale;
      this.scale = clamped;
      this.panX = focalX - this.baseX - imageX * this.scale;
      this.panY = focalY - this.baseY - imageY * this.scale;
      this.clampPan();
      this.applyTransform();
    }

    zoomBy(delta, focalX, focalY) {
      this.setScale(this.scale + delta, focalX, focalY);
    }

    focalFromClient(clientX, clientY) {
      const rect = this.viewport.getBoundingClientRect();
      return {
        x: clientX - rect.left,
        y: clientY - rect.top,
      };
    }

    _bindControls() {
      this.root.querySelectorAll("[data-zoom-action]").forEach((button) => {
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          const action = button.dataset.zoomAction;
          const center = {
            x: this.viewport.clientWidth / 2,
            y: this.viewport.clientHeight / 2,
          };
          if (action === "in") {
            this.zoomBy(ZOOM_STEP, center.x, center.y);
          } else if (action === "out") {
            this.zoomBy(-ZOOM_STEP, center.x, center.y);
          } else if (action === "reset") {
            this.resetView();
          }
        });
      });
    }

    _bindPointer() {
      this.viewport.addEventListener(
        "wheel",
        (event) => {
          event.preventDefault();
          const focal = this.focalFromClient(event.clientX, event.clientY);
          const delta = event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP;
          this.zoomBy(delta, focal.x, focal.y);
        },
        { passive: false }
      );

      this.viewport.addEventListener("pointerdown", (event) => {
        if (event.button !== 0) {
          return;
        }
        this.dragging = true;
        this.lastPointer = { x: event.clientX, y: event.clientY };
        this.viewport.classList.add("is-dragging");
        this.viewport.setPointerCapture(event.pointerId);
      });

      this.viewport.addEventListener("pointermove", (event) => {
        if (!this.dragging) {
          return;
        }
        const dx = event.clientX - this.lastPointer.x;
        const dy = event.clientY - this.lastPointer.y;
        this.lastPointer = { x: event.clientX, y: event.clientY };
        if (this.scale <= 1) {
          return;
        }
        this.panX += dx;
        this.panY += dy;
        this.clampPan();
        this.applyTransform();
      });

      const endDrag = (event) => {
        if (!this.dragging) {
          return;
        }
        this.dragging = false;
        this.viewport.classList.remove("is-dragging");
        if (this.viewport.hasPointerCapture(event.pointerId)) {
          this.viewport.releasePointerCapture(event.pointerId);
        }
      };

      this.viewport.addEventListener("pointerup", endDrag);
      this.viewport.addEventListener("pointercancel", endDrag);
    }
  }

  function layoutViewer(viewer) {
    const maxHeight = readNumber(
      getComputedStyle(document.documentElement).getPropertyValue("--pane-max-height"),
      0
    );
    const grid = viewer.querySelector(".scene-viewer__grid");
    if (!grid) {
      return;
    }

    const paneCount = viewer.classList.contains("scene-viewer--solo-pre") ||
      viewer.classList.contains("scene-viewer--solo-post")
      ? 1
      : 2;
    const slotWidth = grid.clientWidth / paneCount;
    if (!slotWidth) {
      return;
    }

    const referencePane = viewer.querySelector(".pane");
    if (!referencePane) {
      return;
    }

    const aspectWidth = readNumber(referencePane.dataset.aspectWidth, 1);
    const aspectHeight = readNumber(referencePane.dataset.aspectHeight, 1);
    let rowHeight = (slotWidth * aspectHeight) / aspectWidth;
    if (maxHeight > 0 && rowHeight > maxHeight) {
      rowHeight = maxHeight;
    }

    viewer.querySelectorAll(".pane-slot").forEach((slot) => {
      slot.style.height = `${rowHeight}px`;
    });

    viewer._controllers?.forEach((controller) => controller.measure());
  }

  function setViewMode(viewer, mode) {
    viewer.classList.remove("scene-viewer--solo-pre", "scene-viewer--solo-post");
    if (mode === "solo-pre") {
      viewer.classList.add("scene-viewer--solo-pre");
    } else if (mode === "solo-post") {
      viewer.classList.add("scene-viewer--solo-post");
    }
    layoutViewer(viewer);
    viewer._controllers?.forEach((controller) => controller.resetView());
  }

  function bindViewModeControls(viewer) {
    viewer.querySelectorAll("[data-mode-action]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const action = button.dataset.modeAction;
        const paneKey = button.dataset.paneKey;
        if (action === "solo" && paneKey) {
          setViewMode(viewer, `solo-${paneKey}`);
        } else if (action === "split") {
          setViewMode(viewer, "split");
        }
      });
    });
  }

  function initViewer(viewer) {
    const controllers = Array.from(viewer.querySelectorAll(".pane")).map(
      (pane) => new PaneViewport(pane, viewer)
    );
    viewer._controllers = controllers;
    bindViewModeControls(viewer);
    layoutViewer(viewer);

    window.addEventListener("resize", () => layoutViewer(viewer));
    if (typeof ResizeObserver !== "undefined") {
      const grid = viewer.querySelector(".scene-viewer__grid");
      if (grid) {
        new ResizeObserver(() => layoutViewer(viewer)).observe(grid);
      }
    }
  }

  function initAll() {
    document.querySelectorAll(".scene-viewer").forEach(initViewer);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();
