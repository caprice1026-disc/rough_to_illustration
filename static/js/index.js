const initCounters = () => {
  const updateCounter = (textarea) => {
    const targetId = textarea.dataset.counterTarget;
    if (!targetId) return;
    const target = document.getElementById(targetId);
    if (!target) return;
    const max = textarea.getAttribute('maxlength') || textarea.maxLength;
    target.textContent = `${textarea.value.length}/${max}`;
  };

  document.querySelectorAll('[data-counter-target]').forEach((el) => {
    updateCounter(el);
    el.addEventListener('input', () => updateCounter(el));
  });
};

const bindImageUploader = (config) => {
  const fileInput = document.getElementById(config.inputId);
  const previewImage = document.getElementById(config.previewId);
  const placeholder = document.getElementById(config.placeholderId);
  const fileMeta = document.getElementById(config.metaId);
  const dropzone = document.getElementById(config.dropzoneId);
  const clearButton = document.getElementById(config.clearButtonId);

  if (!fileInput || !previewImage || !placeholder || !fileMeta || !dropzone || !clearButton) return null;

  const resetPreview = () => {
    previewImage.classList.add('d-none');
    previewImage.removeAttribute('src');
    placeholder.classList.remove('d-none');
    fileMeta.textContent = '';
    fileInput.value = '';
    if (typeof config.onClear === 'function') {
      config.onClear();
    }
  };

  const handleFile = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      previewImage.src = event.target.result;
      previewImage.classList.remove('d-none');
      placeholder.classList.add('d-none');
      const sizeKb = (file.size / 1024).toFixed(1);
      fileMeta.textContent = `${file.name} / ${sizeKb} KB`;
      if (typeof config.onFile === 'function') {
        config.onFile(file);
      }
    };
    reader.readAsDataURL(file);
  };

  clearButton.addEventListener('click', resetPreview);

  fileInput.addEventListener('change', (event) => {
    const [file] = event.target.files;
    handleFile(file);
  });

  ['dragenter', 'dragover'].forEach((type) => {
    dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dropzone.classList.add('hover');
    });
  });

  ['dragleave', 'drop'].forEach((type) => {
    dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dropzone.classList.remove('hover');
    });
  });

  dropzone.addEventListener('drop', (event) => {
    const [file] = event.dataTransfer.files;
    if (!file) return;
    fileInput.files = event.dataTransfer.files;
    handleFile(file);
  });

  return { resetPreview };
};

const initImagePreviews = () => {
  const editMaskData = document.getElementById('editMaskData');
  const editBaseData = document.getElementById('editBaseData');
  const maskPreview = document.getElementById('editMaskPreviewImage');
  const maskPlaceholder = document.getElementById('editMaskPlaceholder');
  const maskFileMeta = document.getElementById('editMaskFileMeta');
  const resetEditMaskPreview = () => {
    if (maskPreview) {
      maskPreview.classList.add('d-none');
      maskPreview.removeAttribute('src');
    }
    if (maskPlaceholder) maskPlaceholder.classList.remove('d-none');
    if (maskFileMeta) maskFileMeta.textContent = '';
  };
  const clearEditMaskData = () => {
    if (editMaskData) editMaskData.value = '';
    resetEditMaskPreview();
  };
  const clearEditBaseData = () => {
    if (editBaseData) editBaseData.value = '';
  };

  const uploaders = {
    rough: bindImageUploader({
      inputId: 'rough_image',
      previewId: 'roughPreviewImage',
      placeholderId: 'roughPlaceholder',
      metaId: 'roughFileMeta',
      dropzoneId: 'roughDropzone',
      clearButtonId: 'roughClearImage',
    }),
    reference: bindImageUploader({
      inputId: 'reference_image',
      previewId: 'referencePreviewImage',
      placeholderId: 'referencePlaceholder',
      metaId: 'referenceFileMeta',
      dropzoneId: 'referenceDropzone',
      clearButtonId: 'referenceClearImage',
    }),
    editBase: bindImageUploader({
      inputId: 'edit_base_image',
      previewId: 'editBasePreviewImage',
      placeholderId: 'editBasePlaceholder',
      metaId: 'editBaseFileMeta',
      dropzoneId: 'editBaseDropzone',
      clearButtonId: 'editBaseClearImage',
      onFile: () => {
        clearEditMaskData();
        clearEditBaseData();
      },
      onClear: () => {
        clearEditMaskData();
        clearEditBaseData();
      },
    }),
  };

  return { ...uploaders, resetEditMaskPreview };
};

const MODE_SUBMIT_LABELS = {
  rough_with_instructions: 'イラスト生成をリクエスト',
  reference_style_colorize: '参照して着色をリクエスト',
  inpaint_outpaint: '編集をリクエスト',
};

const initModeSwitch = (uploaders) => {
  const modeCards = document.getElementById('modeCards');
  const modeInput = document.getElementById('generationModeInput');
  const modeDescription = document.getElementById('modeDescription');
  const submitLabel = document.getElementById('submitLabel');

  if (!modeCards || !modeInput) return;

  const splitModes = (raw) =>
    String(raw || '')
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);

  const setModeInUrl = (modeId) => {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('mode', modeId);
      window.history.replaceState({}, '', url);
    } catch (error) {
      console.warn('Failed to update mode in URL', error);
    }
  };

  const toggleVisibility = (modeId) => {
    document.querySelectorAll('[data-mode-visible]').forEach((el) => {
      const modes = splitModes(el.dataset.modeVisible);
      const shouldShow = modes.includes(modeId);
      el.classList.toggle('d-none', !shouldShow);
    });
  };

  const applyMode = (modeId, { updateUrl = true } = {}) => {
    modeInput.value = modeId;
    document.querySelectorAll('input[name="mode"]').forEach((input) => {
      input.value = modeId;
    });

    const inputs = modeCards.querySelectorAll('input[data-mode]');
    inputs.forEach((input) => {
      const isActive = input.dataset.mode === modeId;
      input.checked = isActive;
      const card = input.closest('.mode-card');
      if (card) card.classList.toggle('is-active', isActive);
    });

    toggleVisibility(modeId);

    if (submitLabel && MODE_SUBMIT_LABELS[modeId]) {
      submitLabel.textContent = MODE_SUBMIT_LABELS[modeId];
    }

    const activeInput = modeCards.querySelector(`input[data-mode="${modeId}"]`);
    const description = activeInput ? activeInput.dataset.modeDescription : '';
    if (modeDescription) modeDescription.textContent = description || '';

    if (uploaders && uploaders.reference && modeId !== 'reference_style_colorize') {
      uploaders.reference.resetPreview();
    }

    if (uploaders && uploaders.editBase && modeId !== 'inpaint_outpaint') {
      uploaders.editBase.resetPreview();
    }

    if (modeId !== 'inpaint_outpaint') {
      const editMaskData = document.getElementById('editMaskData');
      const editBaseData = document.getElementById('editBaseData');
      if (editMaskData) editMaskData.value = '';
      if (editBaseData) editBaseData.value = '';
      if (uploaders && uploaders.resetEditMaskPreview) uploaders.resetEditMaskPreview();
    }

    if (updateUrl) setModeInUrl(modeId);
  };

  modeCards.querySelectorAll('input[data-mode]').forEach((input) => {
    input.addEventListener('change', () => {
      if (input.disabled) return;
      applyMode(input.dataset.mode);
    });
  });

  applyMode(modeInput.value, { updateUrl: false });
};

const initSubmitState = () => {
  const form = document.getElementById('generateForm');
  const submitBtn = document.getElementById('generateButton');
  const spinner = document.getElementById('loadingSpinner');
  const submitLabel = document.getElementById('submitLabel');
  const statusBadge = document.getElementById('generationStatusBadge');
  const statusText = document.getElementById('generationStatusText');

  if (!form || !submitBtn || !spinner || !submitLabel) return;

  form.addEventListener('submit', () => {
    submitBtn.disabled = true;
    spinner.classList.remove('d-none');
    submitLabel.textContent = '送信中...';
    if (statusBadge) statusBadge.textContent = '生成中';
    if (statusText) statusText.textContent = '生成中です。しばらくお待ちください。';
  });
};

const initPresets = () => {
  const panel = document.getElementById('presetPanel');
  const presetSelect = document.getElementById('presetSelect');
  const deletePresetId = document.getElementById('deletePresetId');
  const applyButton = document.getElementById('applyPreset');
  const presetCreateForm = document.getElementById('presetCreateForm');
  const presetColorInput = document.getElementById('preset_color_value');
  const presetPoseInput = document.getElementById('preset_pose_value');
  const colorTextarea = document.getElementById('color_instruction');
  const poseTextarea = document.getElementById('pose_instruction');

  if (!panel || !presetSelect || !deletePresetId || !applyButton || !presetCreateForm || !presetColorInput || !presetPoseInput || !colorTextarea || !poseTextarea) {
    return;
  }

  let presets = [];
  try {
    const raw = panel.dataset.presets || '[]';
    presets = JSON.parse(raw);
  } catch (error) {
    console.error('プリセットの読み込みに失敗しました', error);
  }

  const findPreset = (presetId) => presets.find((preset) => String(preset.id) === String(presetId));

  const applyPreset = () => {
    const selected = findPreset(presetSelect.value);
    if (!selected) return;

    colorTextarea.value = selected.color || '';
    poseTextarea.value = selected.pose || '';
    colorTextarea.dispatchEvent(new Event('input'));
    poseTextarea.dispatchEvent(new Event('input'));
  };

  const syncDeleteField = () => {
    deletePresetId.value = presetSelect.value || '';
  };

  presetSelect.addEventListener('change', syncDeleteField);
  applyButton.addEventListener('click', applyPreset);
  syncDeleteField();

  presetCreateForm.addEventListener('submit', () => {
    // 現在のテキストエリア内容をプリセットとして保存する
    presetColorInput.value = colorTextarea.value;
    presetPoseInput.value = poseTextarea.value;
  });
};


const initMaskEditor = () => {
  const modalEl = document.getElementById('maskEditorModal');
  const openButton = document.getElementById('openMaskEditorButton');
  const baseInput = document.getElementById('edit_base_image');
  const editMaskData = document.getElementById('editMaskData');
  const editBaseData = document.getElementById('editBaseData');
  const maskPreview = document.getElementById('editMaskPreviewImage');
  const maskPlaceholder = document.getElementById('editMaskPlaceholder');
  const maskFileMeta = document.getElementById('editMaskFileMeta');
  const editModeInput = document.getElementById('editModeInput');
  const editModeButtons = document.querySelectorAll('[data-edit-mode]');
  const baseCanvas = document.getElementById('maskEditorBaseCanvas');
  const maskCanvas = document.getElementById('maskEditorMaskCanvas');
  const brushSizeInput = document.getElementById('maskBrushSize');
  const eraserToggle = document.getElementById('maskEraserToggle');
  const resetButton = document.getElementById('maskResetButton');
  const applyButton = document.getElementById('maskApplyButton');
  const outpaintScale = document.getElementById('outpaintScale');
  const outpaintControls = document.getElementById('outpaintControls');

  if (!modalEl || !baseCanvas || !maskCanvas) return;

  const modal = window.bootstrap ? window.bootstrap.Modal.getOrCreateInstance(modalEl) : null;
  let baseImage = null;
  let isDrawing = false;
  let isErasing = false;
  let currentScale = 1.0;

  const getCurrentMode = () => (editModeInput ? editModeInput.value : 'inpaint');

  const loadImageFromFile = (file) =>
    new Promise((resolve, reject) => {
      if (!file) return reject(new Error('missing file'));
      const reader = new FileReader();
      reader.onload = (event) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = event.target.result;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const renderCanvases = () => {
    if (!baseImage) return;
    const mode = getCurrentMode();
    const scale = mode === 'outpaint' ? currentScale : 1.0;
    const width = Math.max(1, Math.round(baseImage.width * scale));
    const height = Math.max(1, Math.round(baseImage.height * scale));
    const offsetX = Math.round((width - baseImage.width) / 2);
    const offsetY = Math.round((height - baseImage.height) / 2);

    baseCanvas.width = width;
    baseCanvas.height = height;
    maskCanvas.width = width;
    maskCanvas.height = height;

    const baseCtx = baseCanvas.getContext('2d');
    const maskCtx = maskCanvas.getContext('2d');
    if (!baseCtx || !maskCtx) return;

    baseCtx.fillStyle = '#ffffff';
    baseCtx.fillRect(0, 0, width, height);
    baseCtx.drawImage(baseImage, offsetX, offsetY);

    maskCtx.clearRect(0, 0, width, height);
    if (mode === 'outpaint') {
      maskCtx.fillStyle = 'rgba(255, 0, 0, 0.85)';
      maskCtx.fillRect(0, 0, width, height);
      maskCtx.clearRect(offsetX, offsetY, baseImage.width, baseImage.height);
    }
  };

  const setEditMode = (mode) => {
    if (editModeInput) editModeInput.value = mode;
    editModeButtons.forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.editMode === mode);
    });
    if (outpaintControls) outpaintControls.classList.toggle('d-none', mode !== 'outpaint');
    renderCanvases();
  };

  editModeButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const mode = btn.dataset.editMode;
      if (mode) setEditMode(mode);
    });
  });

  if (outpaintScale) {
    const initialScale = parseFloat(outpaintScale.value || '1');
    currentScale = Number.isFinite(initialScale) ? initialScale : 1.0;
    outpaintScale.addEventListener('change', () => {
      const value = parseFloat(outpaintScale.value || '1');
      currentScale = Number.isFinite(value) ? value : 1.0;
      renderCanvases();
    });
  }

  if (eraserToggle) {
    eraserToggle.addEventListener('click', () => {
      isErasing = !isErasing;
      eraserToggle.classList.toggle('active', isErasing);
    });
  }

  if (resetButton) {
    resetButton.addEventListener('click', () => {
      renderCanvases();
    });
  }

  const drawAtEvent = (event) => {
    const rect = maskCanvas.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * maskCanvas.width;
    const y = ((event.clientY - rect.top) / rect.height) * maskCanvas.height;
    const ctx = maskCanvas.getContext('2d');
    if (!ctx) return;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = brushSizeInput ? Number(brushSizeInput.value || 24) : 24;
    ctx.globalCompositeOperation = isErasing ? 'destination-out' : 'source-over';
    ctx.strokeStyle = 'rgba(255, 0, 0, 0.85)';
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + 0.5, y + 0.5);
    ctx.stroke();
  };

  const startDraw = (event) => {
    isDrawing = true;
    drawAtEvent(event);
  };

  const moveDraw = (event) => {
    if (!isDrawing) return;
    const rect = maskCanvas.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * maskCanvas.width;
    const y = ((event.clientY - rect.top) / rect.height) * maskCanvas.height;
    const ctx = maskCanvas.getContext('2d');
    if (!ctx) return;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = brushSizeInput ? Number(brushSizeInput.value || 24) : 24;
    ctx.globalCompositeOperation = isErasing ? 'destination-out' : 'source-over';
    ctx.strokeStyle = 'rgba(255, 0, 0, 0.85)';
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + 0.5, y + 0.5);
    ctx.stroke();
  };

  const stopDraw = () => {
    isDrawing = false;
  };

  maskCanvas.style.touchAction = 'none';
  maskCanvas.addEventListener('pointerdown', startDraw);
  maskCanvas.addEventListener('pointermove', moveDraw);
  maskCanvas.addEventListener('pointerup', stopDraw);
  maskCanvas.addEventListener('pointerleave', stopDraw);

  const openEditor = () => {
    if (!baseImage) {
      alert('編集する画像を先に選択してください。');
      return;
    }
    renderCanvases();
    if (modal) modal.show();
  };

  if (baseInput) {
    baseInput.addEventListener('change', (event) => {
      const [file] = event.target.files;
      if (!file) return;
      loadImageFromFile(file)
        .then((img) => {
          baseImage = img;
          openEditor();
        })
        .catch(() => {
          alert('画像の読み込みに失敗しました。');
        });
    });
  }

  if (openButton) {
    openButton.addEventListener('click', openEditor);
  }

  if (applyButton) {
    applyButton.addEventListener('click', () => {
      if (!baseImage) return;
      if (editMaskData) editMaskData.value = maskCanvas.toDataURL('image/png');
      if (editBaseData) editBaseData.value = baseCanvas.toDataURL('image/png');
      if (maskPreview) {
        maskPreview.src = maskCanvas.toDataURL('image/png');
        maskPreview.classList.remove('d-none');
      }
      if (maskPlaceholder) maskPlaceholder.classList.add('d-none');
      if (maskFileMeta) maskFileMeta.textContent = 'エディタで作成したマスク';
      if (modal) modal.hide();
    });
  }

  setEditMode(getCurrentMode());
};

const bootstrapIndexPage = () => {
  initCounters();
  const uploaders = initImagePreviews();
  initModeSwitch(uploaders);
  initSubmitState();
  initPresets();
  initMaskEditor();
};

document.addEventListener('DOMContentLoaded', bootstrapIndexPage);
