/**
 * JanRakshak AI — Report Issue JS
 * Handles:
 *   1. Multi-step form wizard with GSAP transitions
 *   2. HTML5 Geolocation API — live coordinate capture
 *   3. HTML5 MediaDevices API — in-browser camera capture
 *   4. AJAX form submission with AI analysis response rendering
 *   5. Offline queuing via IndexedDB / Background Sync
 */

// ==========================================================================
// 0. MODULE STATE
// ==========================================================================

const ReportForm = (() => {
  let currentStep = 1;
  const TOTAL_STEPS = 3;

  // Captured data
  let capturedCoords = null;    // { latitude, longitude, accuracy }
  let capturedPhotoBlob = null; // Blob from camera capture
  let capturedPhotoDataUrl = null;
  let uploadedPhotoFileName = "";
  let photoAIAnalysis = null;
  let descriptionTouched = false;

  let mediaStream = null;       // Active camera stream (must be stopped after capture)
  let mapInstance = null;
  let mapMarker = null;

  // ==========================================================================
  // 1. STEP WIZARD
  // ==========================================================================

  /** Transition from one step to the next using GSAP. */
  function goToStep(targetStep) {
    if (targetStep < 1 || targetStep > TOTAL_STEPS) return;

    const currentPanel = document.querySelector(`[data-step="${currentStep}"]`);
    const nextPanel = document.querySelector(`[data-step="${targetStep}"]`);

    if (!currentPanel || !nextPanel) return;

    const direction = targetStep > currentStep ? 1 : -1;

    // Slide current panel out (guard: GSAP may not be loaded yet due to defer)
    if (typeof gsap !== "undefined") {
      gsap.to(currentPanel, {
        x: direction * -40,
        opacity: 0,
        duration: 0.28,
        ease: "power2.in",
        onComplete: () => {
          currentPanel.classList.add("hidden");

          // Slide next panel in from opposite side
          nextPanel.classList.remove("hidden");
          gsap.fromTo(
            nextPanel,
            { x: direction * 40, opacity: 0 },
            { x: 0, opacity: 1, duration: 0.32, ease: "power2.out" }
          );

          currentStep = targetStep;
          updateStepIndicator();
        },
      });
    } else {
      // Fallback: instant swap without animation
      currentPanel.classList.add("hidden");
      nextPanel.classList.remove("hidden");
      currentStep = targetStep;
      updateStepIndicator();
    }
  }

  /** Sync the visual step indicator dots/numbers. */
  function updateStepIndicator() {
    document.querySelectorAll("[data-step-indicator]").forEach((el) => {
      const step = parseInt(el.dataset.stepIndicator, 10);
      el.classList.toggle("step-active", step === currentStep);
      el.classList.toggle("step-complete", step < currentStep);
    });

    // Update progress bar width
    const bar = document.getElementById("step-progress-bar");
    if (bar) {
      const pct = ((currentStep - 1) / (TOTAL_STEPS - 1)) * 100;
      if (typeof gsap !== "undefined") {
        gsap.to(bar, { width: `${pct}%`, duration: 0.4, ease: "power2.out" });
      } else {
        bar.style.width = `${pct}%`;
      }
    }
  }

  function updateDescriptionStatus(text, level = "info") {
    const statusEl = document.getElementById("description-ai-status");
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.remove("hidden", "text-brand-primary", "text-green-600", "text-red-600");
    if (level === "success") {
      statusEl.classList.add("text-green-600");
    } else if (level === "error") {
      statusEl.classList.add("text-red-600");
    } else {
      statusEl.classList.add("text-brand-primary");
    }
  }

  function composeLocationText() {
    const place = document.getElementById("field-location-place")?.value?.trim() || "";
    const street = document.getElementById("field-location-street")?.value?.trim() || "";
    const district = document.getElementById("field-location-district")?.value?.trim() || "";
    const state = document.getElementById("field-location-state")?.value?.trim() || "";
    const full = document.getElementById("field-location")?.value?.trim() || "";

    if (full) return full;
    const parts = [street, place, district, state].filter(Boolean);
    return parts.join(", ");
  }

  // ==========================================================================
  // 2. HTML5 GEOLOCATION API
  // ==========================================================================

  function initGeolocation() {
    const btn = document.getElementById("btn-get-location");
    const statusEl = document.getElementById("geo-status");
    const coordsEl = document.getElementById("geo-coords");
    const mapPin = document.getElementById("geo-map-pin");

    if (!btn) return;

    btn.addEventListener("click", () => {
      if (!("geolocation" in navigator)) {
        showGeoError("Geolocation is not supported by your browser.");
        return;
      }

      btn.disabled = true;
      btn.innerHTML = `
        <span class="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
        Locating…
      `;

      const options = {
        enableHighAccuracy: true,  // Use GPS on mobile devices
        timeout: 15000,            // 15s timeout
        maximumAge: 30000,         // Accept cached position up to 30s old
      };

      navigator.geolocation.getCurrentPosition(
        (position) => onGeoSuccess(position, btn, statusEl, coordsEl, mapPin),
        (error) => onGeoError(error, btn, statusEl),
        options
      );
    });
  }

  async function reverseGeocode(latitude, longitude) {
    try {
      const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}&zoom=18&addressdetails=1`;
      const response = await fetch(url, {
        headers: {
          Accept: "application/json",
        },
      });
      if (!response.ok) {
        throw new Error("Reverse geocoding failed");
      }

      const data = await response.json();
      const address = data.address || {};

      // 1. Extract Landmark / POI if available in Nominatim response
      const poi = address.amenity || address.shop || address.building || address.office || address.tourism || address.historic || address.leisure || "";
      const road = address.road || address.pedestrian || address.footway || address.path || address.cycleway || address.highway || "";
      
      let streetAndLandmark = "";
      if (poi && road) {
        streetAndLandmark = `${road} (Near ${poi})`;
      } else {
        streetAndLandmark = road || poi || "";
      }

      // 2. Extract Place / Area / Locality
      const suburb = address.suburb || address.neighbourhood || address.residential || address.quarter || "";
      const locality = address.village || address.town || address.city_district || "";
      
      const placeParts = [];
      if (suburb) placeParts.push(suburb);
      if (locality && locality !== suburb) placeParts.push(locality);
      const placeAndArea = placeParts.join(", ");

      // 3. Extract City / District / State
      const city = address.city || address.town || address.village || "";
      const district = address.county || address.state_district || "";
      const state = address.state || "";
      const postcode = address.postcode || "";

      // 4. Construct Full Location Description
      const fullLocationParts = [];
      if (streetAndLandmark) fullLocationParts.push(streetAndLandmark);
      if (placeAndArea) fullLocationParts.push(placeAndArea);
      if (city && city !== placeAndArea && city !== suburb && city !== locality) fullLocationParts.push(city);
      if (district && district !== city) {
        const districtName = district.toLowerCase().includes("district") ? district : `${district} District`;
        fullLocationParts.push(districtName);
      }
      if (state) fullLocationParts.push(state);
      
      let fullLocationText = fullLocationParts.join(", ");
      if (postcode) {
        fullLocationText += ` - ${postcode}`;
      }

      const placeInput = document.getElementById("field-location-place");
      const streetInput = document.getElementById("field-location-street");
      const districtInput = document.getElementById("field-location-district");
      const stateInput = document.getElementById("field-location-state");
      const fullInput = document.getElementById("field-location");

      if (placeInput && !placeInput.value.trim()) placeInput.value = placeAndArea || city || "";
      if (streetInput && !streetInput.value.trim()) streetInput.value = streetAndLandmark || "Local Area";
      if (districtInput && !districtInput.value.trim()) districtInput.value = district || city || "";
      if (stateInput && !stateInput.value.trim()) stateInput.value = state || "";

      if (fullInput && !fullInput.value.trim()) {
        fullInput.value = fullLocationText || `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
      }

      if (placeAndArea || streetAndLandmark) {
        JR.toast("Location details fetched automatically.", "success");
      }
    } catch (_) {
      const fullInput = document.getElementById("field-location");
      if (fullInput && !fullInput.value.trim()) {
        fullInput.value = `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
      }
    }
  }

  function updateLocationDetails(latitude, longitude, clearInputs = true) {
    capturedCoords = {
      latitude: latitude,
      longitude: longitude,
      accuracy: capturedCoords ? capturedCoords.accuracy : 0
    };

    // Update coordinate text display
    const coordsEl = document.getElementById("geo-coords");
    if (coordsEl) {
      coordsEl.textContent = `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
      coordsEl.classList.remove("hidden");
    }

    // Populate hidden form fields
    const latField = document.getElementById("field-latitude");
    const lngField = document.getElementById("field-longitude");
    if (latField) latField.value = latitude;
    if (lngField) lngField.value = longitude;

    if (clearInputs) {
      const placeInput = document.getElementById("field-location-place");
      const streetInput = document.getElementById("field-location-street");
      const districtInput = document.getElementById("field-location-district");
      const stateInput = document.getElementById("field-location-state");
      const fullInput = document.getElementById("field-location");
      if (placeInput) placeInput.value = "";
      if (streetInput) streetInput.value = "";
      if (districtInput) districtInput.value = "";
      if (stateInput) stateInput.value = "";
      if (fullInput) fullInput.value = "";
    }

    reverseGeocode(latitude, longitude);
  }

  function onGeoSuccess(position, btn, statusEl, coordsEl, mapPin) {
    const { latitude, longitude, accuracy } = position.coords;
    capturedCoords = { latitude, longitude, accuracy };

    // Update UI
    btn.disabled = false;
    btn.innerHTML = `
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243
             a8 8 0 1111.314 0z"/>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
      </svg>
      Location Captured
    `;
    btn.classList.remove("btn-secondary");
    btn.classList.add("btn-success");

    if (statusEl) {
      statusEl.textContent = `Accuracy: ±${Math.round(accuracy)}m`;
      statusEl.classList.remove("text-slate-500");
      statusEl.classList.add("text-green-600");
    }
    if (coordsEl) {
      coordsEl.textContent = `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
      coordsEl.classList.remove("hidden");
    }

    // Animate the static map pin into view
    if (mapPin) {
      mapPin.classList.remove("hidden");
      if (typeof gsap !== "undefined") {
        gsap.from(mapPin, { scale: 0, opacity: 0, duration: 0.4, ease: "back.out(1.7)" });
      }

      // Initialize / Update Leaflet map preview
      const mapContainer = document.getElementById("geo-map");
      const mapTip = document.getElementById("geo-map-tip");
      if (mapContainer && typeof L !== "undefined") {
        mapContainer.classList.remove("hidden");
        if (mapTip) mapTip.classList.remove("hidden");

        if (!mapInstance) {
          mapInstance = L.map("geo-map", {
            zoomControl: false,
            attributionControl: true
          }).setView([latitude, longitude], 15);

          L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          }).addTo(mapInstance);

          mapMarker = L.marker([latitude, longitude], {
            draggable: true
          }).addTo(mapInstance);

          // Handle marker drag
          mapMarker.on("dragend", function() {
            const pos = mapMarker.getLatLng();
            updateLocationDetails(pos.lat, pos.lng, true);
          });

          // Handle map click
          mapInstance.on("click", function(e) {
            const { lat, lng } = e.latlng;
            mapMarker.setLatLng([lat, lng]);
            updateLocationDetails(lat, lng, true);
          });
        } else {
          mapInstance.setView([latitude, longitude], 15);
          mapMarker.setLatLng([latitude, longitude]);
        }

        // Force Leaflet to recalculate dimensions since the parent container was hidden/animated
        setTimeout(() => {
          if (mapInstance) {
            mapInstance.invalidateSize();
          }
        }, 100);
      }
    }

    // Populate hidden and visible form fields
    updateLocationDetails(latitude, longitude, true);

    JR.toast("Location captured successfully.", "success");
  }

  function onGeoError(error, btn, statusEl) {
    const messages = {
      1: "Location access denied. Please enable it in your browser settings.",
      2: "Location unavailable. Try again in an open area.",
      3: "Location request timed out. Please try again.",
    };
    const msg = messages[error.code] || "An unknown error occurred.";

    btn.disabled = false;
    btn.innerHTML = `Retry Location`;
    if (statusEl) {
      statusEl.textContent = msg;
      statusEl.classList.add("text-red-600");
    }
    JR.toast(msg, "error");
  }

  function showGeoError(msg) {
    JR.toast(msg, "error");
  }

  // ==========================================================================
  // 3. HTML5 CAMERA / MediaDevices API
  // ==========================================================================

  function setPhotoPreview(dataUrl, fileName, blob = null) {
    const dropIdle = document.getElementById("drop-idle");
    const dropPreview = document.getElementById("drop-preview");
    const previewImage = document.getElementById("drop-preview-image");
    const previewName = document.getElementById("drop-preview-name");
    const legacyPreview = document.getElementById("photo-preview");

    capturedPhotoDataUrl = dataUrl;
    capturedPhotoBlob = blob;
    uploadedPhotoFileName = fileName || "issue-photo.jpg";

    if (previewImage) previewImage.src = dataUrl;
    if (previewName) previewName.textContent = uploadedPhotoFileName;
    if (legacyPreview) legacyPreview.src = dataUrl;

    if (dropIdle) dropIdle.classList.add("hidden");
    if (dropPreview) dropPreview.classList.remove("hidden");
  }

  function clearPhotoPreview() {
    const dropIdle = document.getElementById("drop-idle");
    const dropPreview = document.getElementById("drop-preview");
    const previewImage = document.getElementById("drop-preview-image");
    const previewName = document.getElementById("drop-preview-name");
    const uploadInput = document.getElementById("field-photo-upload");
    const aiScanOverlay = document.getElementById("ai-scan-overlay");
    const retakeBtn = document.getElementById("btn-retake-photo");

    capturedPhotoDataUrl = null;
    capturedPhotoBlob = null;
    uploadedPhotoFileName = "";

    if (uploadInput) uploadInput.value = "";
    if (previewImage) previewImage.src = "";
    if (previewName) previewName.textContent = "";
    if (dropPreview) dropPreview.classList.add("hidden");
    if (dropIdle) dropIdle.classList.remove("hidden");
    if (aiScanOverlay) aiScanOverlay.classList.add("hidden");
    if (retakeBtn) retakeBtn.classList.add("hidden");
  }

  function initPhotoUpload() {
    const dropZone = document.getElementById("drop-zone");
    const dropIdle = document.getElementById("drop-idle");
    const browseBtn = document.getElementById("drop-browse");
    const uploadInput = document.getElementById("field-photo-upload");
    const removeBtn = document.getElementById("drop-remove-photo");

    if (!dropZone || !uploadInput || !dropIdle) return;

    const loadFileIntoPreview = (file) => {
      if (!file || !file.type.startsWith("image/")) {
        JR.toast("Please select a valid image file.", "warning");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        JR.toast("Photo size exceeds 10MB.", "warning");
        return;
      }

      const reader = new FileReader();
      reader.onload = (event) => {
        const dataUrl = event.target?.result;
        if (typeof dataUrl === "string") {
          setPhotoPreview(dataUrl, file.name, file);
          analyzeUploadedPhoto(dataUrl);
          JR.toast("Photo uploaded.", "success");
        }
      };
      reader.readAsDataURL(file);
    };

    if (browseBtn) {
      browseBtn.addEventListener("click", () => uploadInput.click());
    }

    dropIdle.addEventListener("click", () => uploadInput.click());

    uploadInput.addEventListener("change", () => {
      if (uploadInput.files && uploadInput.files[0]) {
        loadFileIntoPreview(uploadInput.files[0]);
      }
    });

    dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("drag-over");
    });

    dropZone.addEventListener("dragleave", () => {
      dropZone.classList.remove("drag-over");
    });

    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("drag-over");

      const file = e.dataTransfer?.files?.[0];
      if (!file) return;

      const dt = new DataTransfer();
      dt.items.add(file);
      uploadInput.files = dt.files;
      loadFileIntoPreview(file);
    });

    if (removeBtn) {
      removeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        clearPhotoPreview();
        photoAIAnalysis = null;
        updateDescriptionStatus("Image removed. You can type description manually.", "info");
      });
    }
  }

  async function analyzeUploadedPhoto(photoDataUrl) {
    const aiScanOverlay = document.getElementById("ai-scan-overlay");
    if (aiScanOverlay) {
      aiScanOverlay.classList.remove("hidden");
    }
    updateDescriptionStatus("Analyzing uploaded image with AI...", "info");
    const scanStartTime = Date.now();
    try {
      const response = await fetch("/api/analyze-photo/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          photo_data: photoDataUrl,
          photo_name: uploadedPhotoFileName
        }),
      });

      const data = await response.json();
      if (!response.ok || data.error) {
        throw new Error(data.error || "Image analysis failed");
      }

      photoAIAnalysis = data.analysis || null;
      const autoDescription = data.auto_description || "";
      const descriptionEl = document.getElementById("field-description");

      if (descriptionEl && (!descriptionTouched || !descriptionEl.value.trim())) {
        descriptionEl.value = autoDescription;
      }

      if (photoAIAnalysis && photoAIAnalysis.Issue === "Spam") {
        updateDescriptionStatus("Warning: AI detected this image as irrelevant spam/archive.", "error");
      } else {
        updateDescriptionStatus("AI description generated from photo. You can edit it before submit.", "success");
      }
    } catch (err) {
      photoAIAnalysis = null;
      updateDescriptionStatus(`Photo analysis failed: ${err.message}`, "error");
    } finally {
      // Ensure scan beam VFX completes at least one full sweep pass (1.2s minimum)
      const elapsed = Date.now() - scanStartTime;
      const remainingDelay = Math.max(0, 1200 - elapsed);
      setTimeout(() => {
        if (aiScanOverlay) {
          aiScanOverlay.classList.add("hidden");
        }
      }, remainingDelay);
    }
  }

  function initCamera() {
    const openBtn = document.getElementById("btn-open-camera");
    const captureBtn = document.getElementById("btn-capture-photo");
    const retakeBtn = document.getElementById("btn-retake-photo");
    const videoEl = document.getElementById("camera-video");
    const canvasEl = document.getElementById("camera-canvas");
    const cameraPanel = document.getElementById("camera-panel");

    if (!openBtn) return;

    // Open camera stream
    openBtn.addEventListener("click", async () => {
      try {
        // Request rear camera on mobile (environment), front as fallback
        const constraints = {
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        };

        mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
        videoEl.srcObject = mediaStream;
        await videoEl.play();

        cameraPanel.classList.remove("hidden");
        openBtn.classList.add("hidden");
        captureBtn.classList.remove("hidden");

        if (typeof gsap !== "undefined") {
          gsap.from(cameraPanel, { opacity: 0, scale: 0.97, duration: 0.3 });
        }
      } catch (err) {
        handleCameraError(err);
      }
    });

    // Capture still frame
    captureBtn.addEventListener("click", () => {
      if (!mediaStream) return;

      // Draw current video frame onto canvas
      const ctx = canvasEl.getContext("2d");
      canvasEl.width = videoEl.videoWidth;
      canvasEl.height = videoEl.videoHeight;
      ctx.drawImage(videoEl, 0, 0);

      // Convert canvas to data URL (JPEG, 85% quality)
      capturedPhotoDataUrl = canvasEl.toDataURL("image/jpeg", 0.85);

      // Also prepare a Blob for potential FormData upload
      canvasEl.toBlob(
        (blob) => { capturedPhotoBlob = blob; },
        "image/jpeg",
        0.85
      );

      // Show preview in the drop-zone preview pane, hide camera
      setPhotoPreview(capturedPhotoDataUrl, "captured-photo.jpg", capturedPhotoBlob);
      analyzeUploadedPhoto(capturedPhotoDataUrl);
      cameraPanel.classList.add("hidden");
      captureBtn.classList.add("hidden");
      retakeBtn.classList.remove("hidden");
      openBtn.classList.remove("hidden");

      // Stop camera stream (release hardware resource)
      stopCamera();

      const previewEl = document.getElementById("drop-preview");
      if (typeof gsap !== "undefined" && previewEl) {
        gsap.from(previewEl, { opacity: 0, scale: 0.95, duration: 0.35 });
      }
      JR.toast("Photo captured.", "success");
    });

    // Retake — re-open camera
    retakeBtn.addEventListener("click", () => {
      clearPhotoPreview();
      retakeBtn.classList.add("hidden");
      openBtn.click();
    });
  }

  /** Stop all camera tracks (releases hardware). */
  function stopCamera() {
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }
  }

  function handleCameraError(err) {
    const messages = {
      NotAllowedError: "Camera access denied. Please allow camera permissions.",
      NotFoundError: "No camera found on this device.",
      NotReadableError: "Camera is in use by another application.",
      OverconstrainedError: "Camera does not support the requested settings.",
    };
    const msg = messages[err.name] || `Camera error: ${err.message}`;
    JR.toast(msg, "error");
  }

  // ==========================================================================
  // 4. POPUP MODAL & FORM SUBMISSION
  // ==========================================================================

  let currentPayload = null;
  let currentAnalysis = null;

  function getPriorityBadgeClass(priority) {
    switch ((priority || "").toLowerCase()) {
      case "critical": return "badge-critical";
      case "high": return "badge-high";
      case "medium": return "badge-medium";
      case "low": return "badge-low";
      default: return "badge-unknown";
    }
  }

  function openAIModal(data, payload) {
    currentPayload = payload;
    currentAnalysis = data;

    const modalOverlay = document.getElementById("ai-modal-overlay");
    const modalBox = document.getElementById("ai-modal-box");
    if (!modalOverlay || !modalBox) return;

    const analysis = data.analysis || {};
    const hotspot = data.hotspot || {};
    const dup = data.duplicate || {};

    const safeSet = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val ?? "—";
    };

    safeSet("modal-result-issue", analysis.Issue);
    safeSet("modal-result-department", analysis.Department);
    safeSet("modal-result-confidence", analysis.Confidence);
    safeSet("modal-result-risk", `${analysis["Risk Score"] ?? 0} / 100`);
    safeSet("modal-result-hash", data.privacy_hash || "—");
    safeSet("modal-result-reason", analysis.Reason);
    safeSet("modal-result-action", analysis["Suggested Action"]);
    safeSet("modal-result-advice", analysis.Advice);
    safeSet("modal-result-hotspot", `${hotspot["Hotspot Level"] || ""} — ${hotspot.Recommendation || ""}`);

    // Priority badge
    const badge = document.getElementById("modal-result-priority-badge");
    if (badge) {
      badge.className = `badge text-xs font-semibold px-2 py-0.5 ${getPriorityBadgeClass(analysis.Priority)}`;
      badge.textContent = analysis.Priority || "—";
    }

    // Duplicate warning (auto-upvote on confirm submit)
    const dupEl = document.getElementById("modal-duplicate-warning");
    const dupMsgEl = document.getElementById("modal-duplicate-msg");
    const dupIdText = document.getElementById("dup-report-id-text");
    const upvoteBtn = document.getElementById("btn-upvote-duplicate");

    if (dupEl) {
      if (dup.duplicate && dup.report_id) {
        if (dupMsgEl) {
          dupMsgEl.textContent = `Similar report found: Report #${dup.report_id} (${dup.similarity}% match). On confirm submit, system auto-upvotes existing report and avoids duplicate entry.`;
        }
        if (dupIdText) {
          dupIdText.textContent = dup.report_id;
        }
        if (upvoteBtn) {
          upvoteBtn.classList.add("hidden");
        }
        dupEl.classList.remove("hidden");
      } else {
        dupEl.classList.add("hidden");
        if (upvoteBtn) {
          upvoteBtn.classList.remove("hidden");
        }
      }
    }

    // Reset verification state
    const radTrue = document.querySelector('input[name="ai_verification"][value="true"]');
    if (radTrue) radTrue.checked = true;
    updateVerificationUI(true);

    // Reset success state visibility
    const verificationBox = document.getElementById("modal-verification-box");
    const successState = document.getElementById("modal-success-state");
    const footerActions = document.getElementById("modal-footer-actions");
    
    if (verificationBox) verificationBox.classList.remove("hidden");
    if (successState) successState.classList.add("hidden");
    if (footerActions) footerActions.classList.remove("hidden");

    // Pre-select current department in override dropdown
    const overrideSelect = document.getElementById("modal-override-dept");
    if (overrideSelect && analysis.Department) {
      const matchOpt = Array.from(overrideSelect.options).find(opt => opt.value === analysis.Department);
      if (matchOpt) {
        overrideSelect.value = analysis.Department;
      }
    }

    // Display modal with animation
    modalOverlay.classList.remove("hidden");
    setTimeout(() => {
      modalBox.classList.remove("scale-95", "opacity-0");
      modalBox.classList.add("scale-100", "opacity-100");
    }, 10);
  }

  function closeAIModal() {
    const modalOverlay = document.getElementById("ai-modal-overlay");
    const modalBox = document.getElementById("ai-modal-box");
    if (!modalOverlay || !modalBox) return;

    modalBox.classList.remove("scale-100", "opacity-100");
    modalBox.classList.add("scale-95", "opacity-0");
    setTimeout(() => {
      modalOverlay.classList.add("hidden");
    }, 200);
  }

  function updateVerificationUI(isCorrect) {
    const labelTrue = document.getElementById("label-ai-true");
    const labelFalse = document.getElementById("label-ai-false");
    const container = document.getElementById("override-dept-container");

    if (isCorrect) {
      if (labelTrue) {
        labelTrue.className = "flex items-start gap-2.5 p-3 rounded-lg border-2 border-green-500 bg-green-50/30 cursor-pointer transition";
      }
      if (labelFalse) {
        labelFalse.className = "flex items-start gap-2.5 p-3 rounded-lg border border-slate-200 bg-white cursor-pointer hover:border-amber-400 transition";
      }
      if (container) container.classList.add("hidden");
    } else {
      if (labelTrue) {
        labelTrue.className = "flex items-start gap-2.5 p-3 rounded-lg border border-slate-200 bg-white cursor-pointer hover:border-green-400 transition";
      }
      if (labelFalse) {
        labelFalse.className = "flex items-start gap-2.5 p-3 rounded-lg border-2 border-amber-500 bg-amber-50/30 cursor-pointer transition";
      }
      if (container) container.classList.remove("hidden");
    }
  }

  function initModalEvents() {
    const closeBtn = document.getElementById("modal-close-btn");
    const cancelBtn = document.getElementById("btn-modal-cancel");
    const overlay = document.getElementById("ai-modal-overlay");
    const confirmBtn = document.getElementById("btn-modal-confirm");

    if (closeBtn) closeBtn.addEventListener("click", closeAIModal);
    if (cancelBtn) cancelBtn.addEventListener("click", closeAIModal);
    
    if (overlay) {
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) closeAIModal();
      });
    }

    // Radio toggle events
    document.querySelectorAll('input[name="ai_verification"]').forEach((radio) => {
      radio.addEventListener("change", (e) => {
        updateVerificationUI(e.target.value === "true");
      });
    });

    // Confirm & Submit inside modal
    if (confirmBtn) {
      confirmBtn.addEventListener("click", async () => {
        if (!currentPayload) return;

        const isCorrect = document.querySelector('input[name="ai_verification"]:checked')?.value === "true";
        const overrideDept = document.getElementById("modal-override-dept")?.value || "";

        confirmBtn.disabled = true;
        const originalText = confirmBtn.innerHTML;
        confirmBtn.innerHTML = `
          <span class="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></span>
          Submitting…
        `;

        const finalPayload = {
          ...currentPayload,
          ai_correct: isCorrect,
          corrected_department: !isCorrect ? overrideDept : null,
        };

        try {
          const response = await fetch("/api/submit-report/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify(finalPayload),
          });

          const data = await response.json();
          if (!response.ok || data.error) {
            throw new Error(data.error || "Submission failed");
          }

          // Show success state in modal
          const verificationBox = document.getElementById("modal-verification-box");
          const successState = document.getElementById("modal-success-state");
          const footerActions = document.getElementById("modal-footer-actions");
          const dupWarning = document.getElementById("modal-duplicate-warning");

          if (data.auto_upvoted) {
            JR.toast(`Duplicate found. Report #${data.report_id} upvoted automatically.`, "success");
          } else {
            JR.toast("Report submitted & verified successfully!", "success");
          }

          if (dupWarning) dupWarning.classList.add("hidden");
          if (verificationBox) verificationBox.classList.add("hidden");
          if (footerActions) footerActions.classList.add("hidden");
          if (successState) {
            const titleEl = successState.querySelector("h3") || successState.querySelector("h4");
            const pEl = successState.querySelector("p");
            if (data.auto_upvoted) {
              if (titleEl) titleEl.textContent = `Report #${data.report_id} Upvoted Automatically`;
              if (pEl) pEl.textContent = `Existing report received your support (total upvotes: ${data.upvotes}). New duplicate report was not created.`;
            } else {
              if (titleEl) titleEl.textContent = "Report Submitted Successfully!";
              if (pEl) pEl.textContent = "Your report has been saved and routed to the assigned department.";
            }
            successState.classList.remove("hidden");
          }

        } catch (err) {
          JR.toast(`Submission error: ${err.message}`, "error");
        } finally {
          confirmBtn.disabled = false;
          confirmBtn.innerHTML = originalText;
        }
      });
    }
  }

  function initFormSubmission() {
    const form = document.getElementById("report-form");
    if (!form) return;

    initModalEvents();

    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const description = document.getElementById("field-description").value.trim();
      const location = composeLocationText();
      const submitBtn = document.getElementById("btn-submit");
      const aiScanOverlay = document.getElementById("ai-scan-overlay");
      const hasPhoto = Boolean(capturedPhotoDataUrl);

      if (!description && !hasPhoto) {
        JR.toast("Please add a description or upload a photo before submitting.", "warning");
        const descInput = document.getElementById("field-description");
        if (descInput) descInput.focus();
        return;
      }

      if (!location) {
        JR.toast("Location is required. Please click 'Get My Location' or enter your area/landmark details.", "warning");
        const locInput = document.getElementById("field-location") || document.getElementById("field-location-place");
        if (locInput) locInput.focus();
        return;
      }

      const normalizedDescription = description || photoAIAnalysis?.["Auto Description"] || "Photo evidence submitted for civic issue analysis.";

      submitBtn.disabled = true;
      const originalText = submitBtn.innerHTML;
      submitBtn.innerHTML = `
        <span class="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></span>
        Analyzing AI…
      `;

      if (hasPhoto && aiScanOverlay) {
        aiScanOverlay.classList.remove("hidden");
      }

      const payload = {
        description: normalizedDescription,
        location,
        latitude: capturedCoords?.latitude ?? null,
        longitude: capturedCoords?.longitude ?? null,
        photo_data: capturedPhotoDataUrl,
        photo_name: uploadedPhotoFileName || null,
        photo_ai_analysis: photoAIAnalysis,
      };

      try {
        // Step 1: Call preview analysis to get AI classification & hotspot info for popup
        const response = await fetch("/api/preview-analysis/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (!response.ok || data.error) {
          throw new Error(data.error || "Analysis failed");
        }

        // Step 2: Open verification Pop-up Modal with AI analysis details
        openAIModal(data, payload);

      } catch (err) {
        if (!navigator.onLine) {
          await queueOfflineReport(payload);
          JR.toast("You're offline. Report queued for upload when reconnected.", "warning");
        } else {
          JR.toast(`Analysis failed: ${err.message}`, "error");
        }
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
        if (aiScanOverlay) {
          aiScanOverlay.classList.add("hidden");
        }
      }
    });
  }

  // ==========================================================================
  // 5. OFFLINE INDEXEDDB QUEUE
  // ==========================================================================

  const DB_NAME = "janrakshak-offline";
  const STORE_NAME = "pending-reports";

  function openOfflineDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, 1);
      request.onupgradeneeded = (e) => {
        e.target.result.createObjectStore(STORE_NAME, {
          keyPath: "id",
          autoIncrement: true,
        });
      };
      request.onsuccess = (e) => resolve(e.target.result);
      request.onerror = () => reject(request.error);
    });
  }

  async function queueOfflineReport(payload) {
    try {
      const db = await openOfflineDB();
      const tx = db.transaction(STORE_NAME, "readwrite");
      tx.objectStore(STORE_NAME).add({
        ...payload,
        queued_at: new Date().toISOString(),
      });
      // Register for background sync when supported
      if ("serviceWorker" in navigator && "SyncManager" in window) {
        const reg = await navigator.serviceWorker.ready;
        await reg.sync.register("sync-offline-reports");
      }
    } catch (err) {
      console.error("[Offline Queue] Failed:", err);
    }
  }

  // ==========================================================================
  // 6. CSRF TOKEN HELPER
  // ==========================================================================

  function getCsrfToken() {
    const el = document.querySelector("[name=csrfmiddlewaretoken]");
    if (el) return el.value;

    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
  }

  // ==========================================================================
  // 7. PUBLIC INIT
  // ==========================================================================

  function init() {
    const descriptionEl = document.getElementById("field-description");
    if (descriptionEl) {
      descriptionEl.addEventListener("input", () => {
        descriptionTouched = true;
      });
    }

    initGeolocation();
    initPhotoUpload();
    initCamera();
    initFormSubmission();

    // Wire step navigation buttons
    document.querySelectorAll("[data-go-step]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = parseInt(btn.dataset.goStep, 10);
        goToStep(target);
      });
    });

    updateStepIndicator();
  }

  return { init };
})();

// Bootstrap on DOM ready
document.addEventListener("DOMContentLoaded", ReportForm.init);
