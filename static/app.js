/**
 * Video & Image Watermark Remover — Enterprise Frontend Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements - Workspace & Media
  const uploadDropzone = document.getElementById('uploadDropzone');
  const dropzoneTitle = document.getElementById('dropzoneTitle');
  const dropzoneSubtitle = document.getElementById('dropzoneSubtitle');
  const fileInput = document.getElementById('fileInput');
  const editorWorkspace = document.getElementById('editorWorkspace');
  const videoPlayer = document.getElementById('videoPlayer');
  const imageElement = document.getElementById('imageElement');
  const stageWrapper = document.getElementById('stageWrapper');
  const selectionOverlay = document.getElementById('selectionOverlay');
  const boundingBox = document.getElementById('boundingBox');

  // Video Controls
  const videoControls = document.getElementById('videoControls');
  const btnPlayPause = document.getElementById('btnPlayPause');
  const playIcon = document.getElementById('playIcon');
  const pauseIcon = document.getElementById('pauseIcon');
  const timelineSlider = document.getElementById('timelineSlider');
  const timeCurrent = document.getElementById('timeCurrent');
  const timeTotal = document.getElementById('timeTotal');
  const btnChangeMedia = document.getElementById('btnChangeMedia');

  // Right Panel Elements
  const panelModeTitle = document.getElementById('panelModeTitle');
  const instructionText = document.getElementById('instructionText');
  const accordionToggle = document.getElementById('accordionToggle');
  const accordionBody = document.getElementById('accordionBody');
  const accordionIcon = document.getElementById('accordionIcon');
  const teleaRadiusGroup = document.getElementById('teleaRadiusGroup');
  const crfGroup = document.getElementById('crfGroup');

  // Sliders and Badges
  const radiusInput = document.getElementById('radiusInput');
  const radiusVal = document.getElementById('radiusVal');
  const featherInput = document.getElementById('featherInput');
  const featherVal = document.getElementById('featherVal');
  const paddingInput = document.getElementById('paddingInput');
  const paddingVal = document.getElementById('paddingVal');
  const crfInput = document.getElementById('crfInput');
  const crfVal = document.getElementById('crfVal');

  // Action Buttons
  const btnRemoveWatermark = document.getElementById('btnRemoveWatermark');
  const btnReset = document.getElementById('btnReset');
  const btnTestFrame = document.getElementById('btnTestFrame');

  // Progress & Results
  const progressCard = document.getElementById('progressCard');
  const progressTitle = document.getElementById('progressTitle');
  const progressPercent = document.getElementById('progressPercent');
  const progressBarFill = document.getElementById('progressBarFill');
  const progressSubtext = document.getElementById('progressSubtext');

  const resultCard = document.getElementById('resultCard');
  const resultInfo = document.getElementById('resultInfo');
  const resultPreviewContainer = document.getElementById('resultPreviewContainer');
  const btnDownloadResult = document.getElementById('btnDownloadResult');

  // Sidebar Nav & Theme
  const navButtons = document.querySelectorAll('.sidebar-nav .nav-item');
  const themeToggle = document.getElementById('themeToggle');

  // Application State
  let activeAppMode = 'video'; // 'video', 'image', 'text', 'magic', 'batch'
  let currentFile = null;
  let currentFilename = null;
  let currentMediaType = 'video'; // 'video' or 'image'
  let isPlaying = false;
  let activeTaskId = null;
  let progressPollTimer = null;

  // Bounding Box State (Percentages 0 - 100)
  let boxState = {
    x: 75,
    y: 80,
    w: 18,
    h: 12,
    active: true
  };

  // Interaction State
  let isDraggingBox = false;
  let isResizingBox = false;
  let isDrawingNewBox = false;
  let activeHandle = null;
  let startX = 0, startY = 0;
  let initialBoxPixel = { x: 0, y: 0, w: 0, h: 0 };

  // ========================================================
  // 1. SIDEBAR NAVIGATION & MODE SWITCHING
  // ========================================================
  const switchAppMode = (mode) => {
    activeAppMode = mode;
    navButtons.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-mode') === mode);
    });

    if (mode === 'image') {
      fileInput.accept = 'image/*';
      dropzoneTitle.textContent = 'Open Image to Remove Watermark';
      dropzoneSubtitle.textContent = 'Drag and drop PNG, JPG, WebP, BMP, TIFF, or click below';
      panelModeTitle.textContent = 'Image Cleanup';
      instructionText.textContent = 'Select the watermark or object you want to erase from this photo.';
      crfGroup.style.display = 'none';
      if (currentMediaType === 'image' && editorWorkspace.style.display !== 'none') {
        videoControls.style.display = 'none';
      }
    } else if (mode === 'text') {
      fileInput.accept = 'video/*,image/*';
      dropzoneTitle.textContent = 'Text & Subtitle Remover';
      dropzoneSubtitle.textContent = 'Remove burned-in subtitles, captions, timestamps, or text watermarks';
      panelModeTitle.textContent = 'Text & Subtitle Removal';
      instructionText.textContent = 'Draw a box over subtitles, captions, or text to remove cleanly.';
      paddingInput.value = 3;
      paddingVal.textContent = '3px';
    } else if (mode === 'magic') {
      fileInput.accept = 'video/*,image/*';
      dropzoneTitle.textContent = 'Magic Object Remover';
      dropzoneSubtitle.textContent = 'Remove unwanted people, logos, powerlines, or distractions with AI LaMa';
      panelModeTitle.textContent = 'Magic Object Eraser';
      instructionText.textContent = 'Select any distraction or logo to reconstruct the underlying background.';
    } else if (mode === 'batch') {
      alert('Batch mode activated: You can upload and process videos/images sequentially with saved settings.');
    } else { // default 'video'
      fileInput.accept = 'video/*';
      dropzoneTitle.textContent = 'Open Video to Remove Watermark';
      dropzoneSubtitle.textContent = 'Drag and drop MP4, MOV, WebM, AVI, or click below';
      panelModeTitle.textContent = 'Video Cleanup';
      instructionText.textContent = 'Select the area you want to remove. The watermark will be removed from every frame.';
      crfGroup.style.display = 'flex';
      if (currentMediaType === 'video' && editorWorkspace.style.display !== 'none') {
        videoControls.style.display = 'flex';
      }
    }
  };

  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.getAttribute('data-mode');
      if (mode) switchAppMode(mode);
    });
  });

  // Dark / Light Theme Toggle
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      document.body.classList.toggle('dark-theme');
      document.body.classList.toggle('light-theme');
    });
  }

  // ========================================================
  // 2. ACCORDION & SLIDER CONTROLS
  // ========================================================
  accordionToggle.addEventListener('click', () => {
    const isClosed = accordionBody.style.display === 'none';
    accordionBody.style.display = isClosed ? 'flex' : 'none';
    accordionIcon.textContent = isClosed ? '−' : '+';
  });

  document.querySelectorAll('input[name="modelChoice"]').forEach(r => {
    r.addEventListener('change', (e) => {
      teleaRadiusGroup.style.display = (e.target.value === 'OpenCV Telea') ? 'flex' : 'none';
    });
  });

  const bindSliderBadge = (slider, badge, suffix = '') => {
    slider.addEventListener('input', () => {
      badge.textContent = slider.value + suffix;
    });
  };
  bindSliderBadge(radiusInput, radiusVal, 'px');
  bindSliderBadge(featherInput, featherVal, 'px');
  bindSliderBadge(paddingInput, paddingVal, 'px');
  bindSliderBadge(crfInput, crfVal, '');

  // ========================================================
  // 3. FILE UPLOAD HANDLING (SECURE STREAMING)
  // ========================================================
  const handleFileUpload = async (file) => {
    if (!file) return;
    currentFile = file;

    const formData = new FormData();
    formData.append('file', file);

    progressCard.style.display = 'block';
    progressTitle.textContent = 'Uploading media safely...';
    progressBarFill.style.width = '35%';
    progressPercent.textContent = '35%';
    progressSubtext.textContent = 'Validating file format and streaming to storage...';

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      progressCard.style.display = 'none';

      if (!res.ok || data.detail) {
        alert(data.detail || 'Upload failed.');
        return;
      }

      currentFilename = data.filename;
      currentMediaType = data.media_type;
      crfGroup.style.display = (currentMediaType === 'video') ? 'flex' : 'none';

      uploadDropzone.style.display = 'none';
      editorWorkspace.style.display = 'flex';
      resultCard.style.display = 'none';

      if (currentMediaType === 'video') {
        imageElement.style.display = 'none';
        videoPlayer.style.display = 'block';
        videoControls.style.display = 'flex';
        videoPlayer.src = data.file_url;
        videoPlayer.load();

        videoPlayer.onloadedmetadata = () => {
          timelineSlider.max = videoPlayer.duration || 100;
          timelineSlider.value = 0;
          timeTotal.textContent = formatTime(videoPlayer.duration);
          timeCurrent.textContent = formatTime(0);
          syncOverlaySize();
          renderBoundingBox();
        };
      } else {
        videoPlayer.style.display = 'none';
        videoControls.style.display = 'none';
        imageElement.style.display = 'block';
        imageElement.src = data.file_url;

        imageElement.onload = () => {
          syncOverlaySize();
          renderBoundingBox();
        };
      }
    } catch (err) {
      progressCard.style.display = 'none';
      alert('Upload error: ' + err.message);
    }
  };

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFileUpload(e.target.files[0]);
  });

  btnChangeMedia.addEventListener('click', () => {
    uploadDropzone.style.display = 'flex';
    editorWorkspace.style.display = 'none';
    if (videoPlayer) videoPlayer.pause();
  });

  // Drag & drop on dropzone
  uploadDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadDropzone.classList.add('dragover');
  });
  uploadDropzone.addEventListener('dragleave', () => uploadDropzone.classList.remove('dragover'));
  uploadDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadDropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleFileUpload(e.dataTransfer.files[0]);
  });

  // ========================================================
  // 4. VIDEO TIMELINE & PLAYBACK
  // ========================================================
  btnPlayPause.addEventListener('click', () => {
    if (videoPlayer.paused) {
      videoPlayer.play();
      playIcon.style.display = 'none';
      pauseIcon.style.display = 'block';
      isPlaying = true;
    } else {
      videoPlayer.pause();
      playIcon.style.display = 'block';
      pauseIcon.style.display = 'none';
      isPlaying = false;
    }
  });

  videoPlayer.addEventListener('timeupdate', () => {
    timelineSlider.value = videoPlayer.currentTime;
    timeCurrent.textContent = formatTime(videoPlayer.currentTime);
  });

  timelineSlider.addEventListener('input', () => {
    videoPlayer.currentTime = parseFloat(timelineSlider.value);
    timeCurrent.textContent = formatTime(videoPlayer.currentTime);
  });

  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '00:00.0';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  // ========================================================
  // 5. BOUNDING BOX POSITIONING & RESIZING ENGINE
  // ========================================================
  const getRenderedMediaRect = () => {
    const el = (currentMediaType === 'video') ? videoPlayer : imageElement;
    if (!el) return null;

    const nw = (currentMediaType === 'video') ? el.videoWidth : el.naturalWidth;
    const nh = (currentMediaType === 'video') ? el.videoHeight : el.naturalHeight;
    if (!nw || !nh) return null;

    const cw = el.clientWidth;
    const ch = el.clientHeight;
    const mediaAspect = nw / nh;
    const containerAspect = cw / ch;

    let rw, rh, rx, ry;
    if (containerAspect > mediaAspect) {
      rh = ch;
      rw = rh * mediaAspect;
      ry = 0;
      rx = (cw - rw) / 2;
    } else {
      rw = cw;
      rh = rw / mediaAspect;
      rx = 0;
      ry = (ch - rh) / 2;
    }

    const stageRect = stageWrapper.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();

    return {
      left: elRect.left - stageRect.left + rx,
      top: elRect.top - stageRect.top + ry,
      width: rw,
      height: rh,
      naturalW: nw,
      naturalH: nh
    };
  };

  const syncOverlaySize = () => {
    const r = getRenderedMediaRect();
    if (!r) return;
    selectionOverlay.style.left = `${r.left}px`;
    selectionOverlay.style.top = `${r.top}px`;
    selectionOverlay.style.width = `${r.width}px`;
    selectionOverlay.style.height = `${r.height}px`;
  };

  window.addEventListener('resize', () => {
    syncOverlaySize();
    renderBoundingBox();
  });

  const renderBoundingBox = () => {
    if (!boxState.active) {
      boundingBox.style.display = 'none';
      return;
    }
    const r = getRenderedMediaRect();
    if (!r) return;

    const px = (boxState.x / 100) * r.width;
    const py = (boxState.y / 100) * r.height;
    const pw = (boxState.w / 100) * r.width;
    const ph = (boxState.h / 100) * r.height;

    boundingBox.style.left = `${px}px`;
    boundingBox.style.top = `${py}px`;
    boundingBox.style.width = `${pw}px`;
    boundingBox.style.height = `${ph}px`;
    boundingBox.style.display = 'block';
  };

  // Direct Interactive Mouse Events
  selectionOverlay.addEventListener('mousedown', (e) => {
    const overlayRect = selectionOverlay.getBoundingClientRect();
    const clickX = e.clientX - overlayRect.left;
    const clickY = e.clientY - overlayRect.top;

    if (e.target.classList.contains('handle')) {
      isResizingBox = true;
      activeHandle = e.target.getAttribute('data-handle');
      startX = e.clientX;
      startY = e.clientY;

      const r = getRenderedMediaRect();
      initialBoxPixel = {
        x: (boxState.x / 100) * r.width,
        y: (boxState.y / 100) * r.height,
        w: (boxState.w / 100) * r.width,
        h: (boxState.h / 100) * r.height
      };
      e.stopPropagation();
    } else if (e.target.closest('#boundingBox')) {
      isDraggingBox = true;
      startX = e.clientX;
      startY = e.clientY;

      const r = getRenderedMediaRect();
      initialBoxPixel = {
        x: (boxState.x / 100) * r.width,
        y: (boxState.y / 100) * r.height,
        w: (boxState.w / 100) * r.width,
        h: (boxState.h / 100) * r.height
      };
      e.stopPropagation();
    } else {
      isDrawingNewBox = true;
      startX = clickX;
      startY = clickY;

      const r = getRenderedMediaRect();
      boxState.x = Math.max(0, Math.min(100, (clickX / r.width) * 100));
      boxState.y = Math.max(0, Math.min(100, (clickY / r.height) * 100));
      boxState.w = 1;
      boxState.h = 1;
      boxState.active = true;
      renderBoundingBox();
    }
  });

  window.addEventListener('mousemove', (e) => {
    const r = getRenderedMediaRect();
    if (!r) return;

    if (isDraggingBox) {
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;

      let newPx = Math.max(0, Math.min(r.width - initialBoxPixel.w, initialBoxPixel.x + dx));
      let newPy = Math.max(0, Math.min(r.height - initialBoxPixel.h, initialBoxPixel.y + dy));

      boxState.x = (newPx / r.width) * 100;
      boxState.y = (newPy / r.height) * 100;
      renderBoundingBox();
    } else if (isResizingBox) {
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;

      let { x, y, w, h } = initialBoxPixel;
      const minSize = 15;

      if (activeHandle.includes('e')) w = Math.max(minSize, Math.min(r.width - x, w + dx));
      if (activeHandle.includes('s')) h = Math.max(minSize, Math.min(r.height - y, h + dy));
      if (activeHandle.includes('w')) {
        const potentialW = w - dx;
        if (potentialW >= minSize && x + dx >= 0) {
          x += dx;
          w = potentialW;
        }
      }
      if (activeHandle.includes('n')) {
        const potentialH = h - dy;
        if (potentialH >= minSize && y + dy >= 0) {
          y += dy;
          h = potentialH;
        }
      }

      boxState.x = (x / r.width) * 100;
      boxState.y = (y / r.height) * 100;
      boxState.w = (w / r.width) * 100;
      boxState.h = (h / r.height) * 100;
      renderBoundingBox();
    } else if (isDrawingNewBox) {
      const overlayRect = selectionOverlay.getBoundingClientRect();
      const curX = Math.max(0, Math.min(r.width, e.clientX - overlayRect.left));
      const curY = Math.max(0, Math.min(r.height, e.clientY - overlayRect.top));

      const bx = Math.min(startX, curX);
      const by = Math.min(startY, curY);
      const bw = Math.abs(curX - startX);
      const bh = Math.abs(curY - startY);

      boxState.x = (bx / r.width) * 100;
      boxState.y = (by / r.height) * 100;
      boxState.w = (bw / r.width) * 100;
      boxState.h = (bh / r.height) * 100;
      renderBoundingBox();
    }
  });

  window.addEventListener('mouseup', () => {
    isDraggingBox = false;
    isResizingBox = false;
    isDrawingNewBox = false;
    activeHandle = null;
  });

  btnReset.addEventListener('click', () => {
    boxState = { x: 75, y: 80, w: 18, h: 12, active: true };
    renderBoundingBox();
    resultCard.style.display = 'none';
  });

  // ========================================================
  // 6. PROCESS MEDIA (FULL INPAINTING)
  // ========================================================
  btnRemoveWatermark.addEventListener('click', async () => {
    if (!currentFile && !currentFilename) {
      alert('Please upload a video or image first.');
      return;
    }

    const model = document.querySelector('input[name="modelChoice"]:checked').value;
    const radius = parseInt(radiusInput.value);
    const feather = parseInt(featherInput.value);
    const padding = parseInt(paddingInput.value);
    const crf = parseInt(crfInput.value);

    const payload = {
      media_type: currentMediaType,
      filename: currentFilename,
      x: boxState.x,
      y: boxState.y,
      w: boxState.w,
      h: boxState.h,
      model,
      radius,
      feather,
      padding,
      crf
    };

    btnRemoveWatermark.disabled = true;
    progressCard.style.display = 'block';
    progressTitle.textContent = 'Processing Media...';
    progressBarFill.style.width = '5%';
    progressPercent.textContent = '5%';
    progressSubtext.textContent = 'Initializing inpainting pipeline...';
    resultCard.style.display = 'none';

    try {
      const res = await fetch('/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!res.ok || data.detail) {
        alert(data.detail || 'Inpainting failed to start.');
        btnRemoveWatermark.disabled = false;
        progressCard.style.display = 'none';
        return;
      }

      activeTaskId = data.task_id;
      pollProgress(activeTaskId);
    } catch (err) {
      btnRemoveWatermark.disabled = false;
      progressCard.style.display = 'none';
      alert('Processing error: ' + err.message);
    }
  });

  const pollProgress = (taskId) => {
    if (progressPollTimer) clearInterval(progressPollTimer);

    progressPollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/progress/${taskId}`);
        const data = await res.json();

        if (data.status === 'processing') {
          const pct = Math.round(data.progress * 100);
          progressBarFill.style.width = `${pct}%`;
          progressPercent.textContent = `${pct}%`;
          progressSubtext.textContent = data.message || `Frame ${data.current_frame} of ${data.total_frames}`;
        } else if (data.status === 'complete') {
          clearInterval(progressPollTimer);
          btnRemoveWatermark.disabled = false;
          progressCard.style.display = 'none';

          resultCard.style.display = 'flex';
          resultInfo.textContent = data.message || 'File cleaned successfully!';
          btnDownloadResult.href = data.download_url;
          btnDownloadResult.setAttribute('download', data.filename);

          if (currentMediaType === 'video') {
            resultPreviewContainer.innerHTML = `<video src="${data.file_url}" controls autoplay loop></video>`;
          } else {
            resultPreviewContainer.innerHTML = `<img src="${data.file_url}" alt="Cleaned Result">`;
          }
        } else if (data.status === 'error') {
          clearInterval(progressPollTimer);
          btnRemoveWatermark.disabled = false;
          progressCard.style.display = 'none';
          alert('Inpainting failed: ' + (data.error || 'Unknown error'));
        }
      } catch (err) {
        console.error('Progress polling error:', err);
      }
    }, 400);
  };

  // ========================================================
  // 7. TEST ON CURRENT FRAME
  // ========================================================
  btnTestFrame.addEventListener('click', async () => {
    if (!currentFile && !currentFilename) {
      alert('Please upload a video or image first.');
      return;
    }

    const model = document.querySelector('input[name="modelChoice"]:checked').value;
    const radius = parseInt(radiusInput.value);
    const feather = parseInt(featherInput.value);
    const padding = parseInt(paddingInput.value);
    const timestamp = (currentMediaType === 'video') ? videoPlayer.currentTime : 0;

    btnTestFrame.textContent = '⏳ Testing Frame...';
    btnTestFrame.disabled = true;

    try {
      const res = await fetch('/api/test-frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          media_type: currentMediaType,
          filename: currentFilename,
          timestamp,
          x: boxState.x,
          y: boxState.y,
          w: boxState.w,
          h: boxState.h,
          model,
          radius,
          feather,
          padding
        })
      });
      const data = await res.json();
      btnTestFrame.textContent = '⚡ Quick Test on Current Frame';
      btnTestFrame.disabled = false;

      if (!res.ok || data.detail) {
        alert(data.detail || 'Test failed.');
        return;
      }

      resultCard.style.display = 'flex';
      resultInfo.textContent = `Test Frame Result (${data.elapsed.toFixed(2)}s)`;
      btnDownloadResult.href = data.file_url;
      btnDownloadResult.setAttribute('download', 'test_frame_cleaned.png');
      resultPreviewContainer.innerHTML = `<img src="${data.file_url}" alt="Test Result">`;
    } catch (err) {
      btnTestFrame.textContent = '⚡ Quick Test on Current Frame';
      btnTestFrame.disabled = false;
      alert('Test error: ' + err.message);
    }
  });
});
