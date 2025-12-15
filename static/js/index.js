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

const initImagePreview = () => {
  const fileInput = document.getElementById('rough_image');
  const previewImage = document.getElementById('previewImage');
  const placeholder = document.getElementById('uploadPlaceholder');
  const fileMeta = document.getElementById('fileMeta');
  const dropzone = document.getElementById('uploadDropzone');
  const clearButton = document.getElementById('clearImage');

  if (!fileInput || !previewImage || !placeholder || !fileMeta || !dropzone || !clearButton) return;

  const resetPreview = () => {
    previewImage.classList.add('d-none');
    previewImage.removeAttribute('src');
    placeholder.classList.remove('d-none');
    fileMeta.textContent = '';
    fileInput.value = '';
  };

  const handleFile = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImage.src = e.target.result;
      previewImage.classList.remove('d-none');
      placeholder.classList.add('d-none');
      const sizeKb = (file.size / 1024).toFixed(1);
      fileMeta.textContent = `${file.name} / ${sizeKb} KB`;
    };
    reader.readAsDataURL(file);
  };

  clearButton.addEventListener('click', () => resetPreview());

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

const bootstrapIndexPage = () => {
  initCounters();
  initImagePreview();
  initSubmitState();
  initPresets();
};

document.addEventListener('DOMContentLoaded', bootstrapIndexPage);
