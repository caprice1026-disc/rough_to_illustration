const state = {
  user: null,
  modes: [],
  chatModes: [],
  options: { aspect_ratio_options: [], resolution_options: [] },
  presets: [],
  sessions: [],
  currentSessionId: null,
  currentView: 'generate',
  lastResult: null,
  csrfToken: null,
};

const elements = {};

const cacheElements = () => {
  elements.statusArea = document.getElementById('statusArea');
  elements.loginView = document.getElementById('loginView');
  elements.appView = document.getElementById('appView');
  elements.loginForm = document.getElementById('loginForm');
  elements.loginUsername = document.getElementById('loginUsername');
  elements.loginPassword = document.getElementById('loginPassword');
  elements.navUserBadge = document.getElementById('navUserBadge');
  elements.navViews = document.getElementById('navViews');
  elements.logoutButton = document.getElementById('logoutButton');
  elements.generateView = document.getElementById('generateView');
  elements.chatView = document.getElementById('chatView');
  elements.adminView = document.getElementById('adminView');
  elements.generationMode = document.getElementById('generationMode');
  elements.generationModeDescription = document.getElementById('generationModeDescription');
  elements.generateForm = document.getElementById('generateForm');
  elements.generateSpinner = document.getElementById('generateSpinner');
  elements.generateButtonLabel = document.getElementById('generateButtonLabel');
  elements.generationStatusBadge = document.getElementById('generationStatusBadge');
  elements.generationOptions = document.getElementById('generationOptions');
  elements.aspectRatioSelect = document.getElementById('aspectRatioSelect');
  elements.resolutionSelect = document.getElementById('resolutionSelect');
  elements.resultImage = document.getElementById('resultImage');
  elements.resultPlaceholder = document.getElementById('resultPlaceholder');
  elements.downloadLink = document.getElementById('downloadLink');
  elements.presetSelect = document.getElementById('presetSelect');
  elements.applyPreset = document.getElementById('applyPreset');
  elements.deletePreset = document.getElementById('deletePreset');
  elements.presetForm = document.getElementById('presetForm');
  elements.presetName = document.getElementById('presetName');
  elements.chatSessionList = document.getElementById('chatSessionList');
  elements.newSessionButton = document.getElementById('newSessionButton');
  elements.chatMessages = document.getElementById('chatMessages');
  elements.chatForm = document.getElementById('chatForm');
  elements.chatSessionId = document.getElementById('chatSessionId');
  elements.chatModeSelect = document.getElementById('chatModeSelect');
  elements.chatModeHelper = document.getElementById('chatModeHelper');
  elements.currentSessionBadge = document.getElementById('currentSessionBadge');
  elements.chatStatus = document.getElementById('chatStatus');
  elements.signupForm = document.getElementById('signupForm');
  elements.signupUsername = document.getElementById('signupUsername');
  elements.signupEmail = document.getElementById('signupEmail');
  elements.signupPassword = document.getElementById('signupPassword');
};

const showStatus = (message, type = 'info') => {
  if (!elements.statusArea) return;
  const wrapper = document.createElement('div');
  wrapper.className = `alert alert-${type} alert-dismissible fade show flash-card`;
  wrapper.setAttribute('role', 'alert');
  wrapper.innerHTML = `<i class="bi bi-info-circle me-2"></i>${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
  elements.statusArea.appendChild(wrapper);
  setTimeout(() => {
    try {
      const alertApi = window.bootstrap?.Alert;
      if (alertApi) {
        const alertInstance = alertApi.getOrCreateInstance(wrapper);
        alertInstance.close();
      } else {
        wrapper.remove();
      }
    } catch (error) {
      wrapper.remove();
    }
  }, 5200);
};

const clearStatus = () => {
  if (!elements.statusArea) return;
  elements.statusArea.innerHTML = '';
};

const fetchCsrfToken = async () => {
  const response = await fetch('/api/csrf', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  const payload = await response.json();
  state.csrfToken = payload.csrf_token || null;
  return state.csrfToken;
};

const ensureCsrfToken = async () => {
  if (state.csrfToken) return state.csrfToken;
  return fetchCsrfToken();
};

const apiFetch = async (url, options = {}) => {
  const headers = options.headers ? { ...options.headers } : {};
  const method = (options.method || 'GET').toUpperCase();
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = await ensureCsrfToken();
    if (token) headers['X-CSRFToken'] = token;
  }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }
  headers['Accept'] = headers['Accept'] || 'application/json';

  const response = await fetch(url, {
    credentials: 'same-origin',
    ...options,
    headers,
  });

  const contentType = response.headers.get('content-type') || '';
  const hasJson = contentType.includes('application/json');
  const payload = hasJson ? await response.json() : {};

  if (response.status === 401) {
    setLoggedOut();
    throw new Error(payload.error || 'ログインが必要です。');
  }

  if (!response.ok) {
    throw new Error(payload.error || '通信に失敗しました。');
  }

  return payload;
};

const setLoggedOut = () => {
  state.user = null;
  state.presets = [];
  state.sessions = [];
  state.currentSessionId = null;
  state.lastResult = null;
  clearStatus();
  renderLogin();
};

const renderLogin = () => {
  if (elements.loginView) elements.loginView.classList.remove('d-none');
  if (elements.appView) elements.appView.classList.add('d-none');
  if (elements.navUserBadge) elements.navUserBadge.classList.add('d-none');
  if (elements.navViews) elements.navViews.classList.add('d-none');
  if (elements.logoutButton) elements.logoutButton.classList.add('d-none');
};

const renderApp = () => {
  if (elements.loginView) elements.loginView.classList.add('d-none');
  if (elements.appView) elements.appView.classList.remove('d-none');
  if (elements.navUserBadge && state.user) {
    elements.navUserBadge.textContent = `${state.user.username} さん`;
    elements.navUserBadge.classList.remove('d-none');
  }
  if (elements.navViews) elements.navViews.classList.remove('d-none');
  if (elements.logoutButton) elements.logoutButton.classList.remove('d-none');
  if (elements.adminView) {
    elements.adminView.classList.toggle('d-none', !state.user?.is_initial_user);
  }
  setView(state.currentView);
};

const setView = (viewName) => {
  state.currentView = viewName;
  if (elements.generateView) elements.generateView.classList.toggle('d-none', viewName !== 'generate');
  if (elements.chatView) elements.chatView.classList.toggle('d-none', viewName !== 'chat');
  if (elements.navViews) {
    elements.navViews.querySelectorAll('button[data-view]').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.view === viewName);
    });
  }
  if (viewName === 'chat') {
    ensureChatReady();
  }
};

const populateModes = () => {
  if (!elements.generationMode) return;
  elements.generationMode.innerHTML = '';
  state.modes
    .filter((mode) => mode.enabled && mode.id !== 'chat_mode')
    .forEach((mode) => {
      const option = document.createElement('option');
      option.value = mode.id;
      option.textContent = mode.label;
      elements.generationMode.appendChild(option);
    });
};

const populateChatModes = () => {
  if (!elements.chatModeSelect) return;
  elements.chatModeSelect.innerHTML = '';
  state.chatModes.forEach((mode) => {
    const option = document.createElement('option');
    option.value = mode.id;
    option.textContent = mode.label;
    elements.chatModeSelect.appendChild(option);
  });
};

const populateOptions = () => {
  if (elements.aspectRatioSelect) {
    elements.aspectRatioSelect.innerHTML = '';
    state.options.aspect_ratio_options.forEach((label) => {
      const option = document.createElement('option');
      option.value = label;
      option.textContent = label === 'auto' ? '自動' : label;
      elements.aspectRatioSelect.appendChild(option);
    });
  }

  if (elements.resolutionSelect) {
    elements.resolutionSelect.innerHTML = '';
    state.options.resolution_options.forEach((label) => {
      const option = document.createElement('option');
      option.value = label;
      option.textContent = label === 'auto' ? '自動' : label;
      elements.resolutionSelect.appendChild(option);
    });
  }
};

const updateModePanels = (modeId) => {
  const panels = document.querySelectorAll('[data-mode-panel]');
  panels.forEach((panel) => {
    const isActive = panel.dataset.modePanel === modeId;
    panel.classList.toggle('d-none', !isActive);
    panel.querySelectorAll('input, textarea, select').forEach((input) => {
      input.disabled = !isActive;
    });
  });

  if (elements.generationOptions) {
    const showOptions = modeId !== 'inpaint_outpaint';
    elements.generationOptions.classList.toggle('d-none', !showOptions);
    elements.generationOptions.querySelectorAll('select').forEach((select) => {
      select.disabled = !showOptions;
    });
  }

  const description = state.modes.find((mode) => mode.id === modeId)?.description || '';
  if (elements.generationModeDescription) {
    elements.generationModeDescription.textContent = description;
  }
};

const renderPresets = () => {
  if (!elements.presetSelect) return;
  elements.presetSelect.innerHTML = '';
  if (state.presets.length === 0) {
    const option = document.createElement('option');
    option.textContent = 'プリセットなし';
    option.disabled = true;
    option.selected = true;
    elements.presetSelect.appendChild(option);
    return;
  }
  state.presets.forEach((preset) => {
    const option = document.createElement('option');
    option.value = String(preset.id);
    option.textContent = preset.name;
    elements.presetSelect.appendChild(option);
  });
};

const findPreset = () => {
  const presetId = elements.presetSelect?.value;
  if (!presetId) return null;
  return state.presets.find((preset) => String(preset.id) === String(presetId)) || null;
};

const applyPreset = () => {
  const preset = findPreset();
  if (!preset) return;

  const modeId = elements.generationMode?.value || 'rough_with_instructions';
  if (modeId === 'reference_style_colorize') {
    const referenceInstruction = document.getElementById('referenceInstruction');
    if (referenceInstruction) referenceInstruction.value = preset.color_instruction || '';
  } else if (modeId === 'inpaint_outpaint') {
    const editInstruction = document.getElementById('editInstruction');
    if (editInstruction) editInstruction.value = preset.color_instruction || '';
  } else {
    const colorInstruction = document.getElementById('colorInstruction');
    const poseInstruction = document.getElementById('poseInstruction');
    if (colorInstruction) colorInstruction.value = preset.color_instruction || '';
    if (poseInstruction) poseInstruction.value = preset.pose_instruction || '';
  }
};

const buildPresetPayload = () => {
  const modeId = elements.generationMode?.value || 'rough_with_instructions';
  const name = elements.presetName?.value.trim() || '';

  if (modeId === 'reference_style_colorize') {
    const referenceInstruction = document.getElementById('referenceInstruction');
    return {
      mode: modeId,
      name,
      color_instruction: referenceInstruction?.value || '',
      pose_instruction: '',
    };
  }

  if (modeId === 'inpaint_outpaint') {
    const editInstruction = document.getElementById('editInstruction');
    return {
      mode: modeId,
      name,
      color_instruction: editInstruction?.value || '',
      pose_instruction: '',
    };
  }

  const colorInstruction = document.getElementById('colorInstruction');
  const poseInstruction = document.getElementById('poseInstruction');
  return {
    mode: modeId,
    name,
    color_instruction: colorInstruction?.value || '',
    pose_instruction: poseInstruction?.value || '',
  };
};

const renderResult = (result) => {
  if (!elements.resultImage || !elements.resultPlaceholder || !elements.downloadLink) return;
  if (!result) {
    elements.resultImage.classList.add('d-none');
    elements.resultPlaceholder.classList.remove('d-none');
    elements.downloadLink.classList.add('d-none');
    return;
  }

  elements.resultPlaceholder.classList.add('d-none');
  elements.resultImage.src = result.image_data_uri;
  elements.resultImage.classList.remove('d-none');

  const ext = result.mime_type === 'image/jpeg' ? 'jpg' : 'png';
  elements.downloadLink.href = result.image_data_uri;
  elements.downloadLink.download = `generated_image.${ext}`;
  elements.downloadLink.classList.remove('d-none');
};

const toggleGenerationLoading = (isLoading) => {
  if (elements.generateSpinner) elements.generateSpinner.classList.toggle('d-none', !isLoading);
  if (elements.generateButtonLabel) {
    elements.generateButtonLabel.textContent = isLoading ? '生成中...' : '生成をリクエスト';
  }
  if (elements.generationStatusBadge) {
    elements.generationStatusBadge.textContent = isLoading ? '生成中' : '準備完了';
  }
};

const toggleChatExtras = (modeId) => {
  document.querySelectorAll('[data-mode-visible]').forEach((el) => {
    const modes = String(el.dataset.modeVisible || '')
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);
    const shouldShow = modes.includes(modeId);
    el.classList.toggle('d-none', !shouldShow);
    el.querySelectorAll('input, textarea, select').forEach((input) => {
      input.disabled = !shouldShow;
    });
  });

  const mode = state.chatModes.find((item) => item.id === modeId);
  if (elements.chatModeHelper) {
    elements.chatModeHelper.textContent = mode?.helper || 'モードを選択して送信します。';
  }
};

const renderChatSessions = () => {
  if (!elements.chatSessionList) return;
  elements.chatSessionList.innerHTML = '';
  state.sessions.forEach((session) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'list-group-item list-group-item-action';
    if (session.id === state.currentSessionId) item.classList.add('active');
    item.dataset.sessionId = session.id;
    item.innerHTML = `
      <div class="fw-semibold">${session.title}</div>
      <small class="text-white-50">${session.updated_at || ''}</small>
    `;
    elements.chatSessionList.appendChild(item);
  });
};

const renderChatMessages = (messages) => {
  if (!elements.chatMessages) return;
  elements.chatMessages.innerHTML = '';
  if (!messages || messages.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'empty-chat';
    empty.textContent = 'まだメッセージがありません。まずはテキストを送信してください。';
    elements.chatMessages.appendChild(empty);
    return;
  }
  messages.forEach((message) => {
    const wrapper = document.createElement('div');
    wrapper.className = `chat-message ${message.role === 'user' ? 'is-user' : 'is-assistant'}`;
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';

    const meta = document.createElement('div');
    meta.className = 'chat-meta';
    const role = document.createElement('span');
    role.className = 'chat-role';
    role.textContent = message.role === 'user' ? 'あなた' : 'アシスタント';
    meta.appendChild(role);
    if (message.mode_id) {
      const mode = document.createElement('span');
      mode.className = 'chat-mode';
      mode.textContent = message.mode_id;
      meta.appendChild(mode);
    }
    bubble.appendChild(meta);

    if (message.text) {
      const text = document.createElement('div');
      text.className = 'chat-text';
      text.textContent = message.text;
      bubble.appendChild(text);
    }

    if (Array.isArray(message.attachments) && message.attachments.length > 0) {
      const attachmentWrap = document.createElement('div');
      attachmentWrap.className = 'chat-attachments';
      message.attachments.forEach((attachment) => {
        const card = document.createElement('div');
        card.className = 'chat-attachment';
        const img = document.createElement('img');
        img.src = attachment.url;
        img.alt = '添付画像';
        card.appendChild(img);
        const label = document.createElement('div');
        label.className = 'chat-attachment-label';
        label.textContent = attachment.kind || 'image';
        card.appendChild(label);
        attachmentWrap.appendChild(card);
      });
      bubble.appendChild(attachmentWrap);
    }

    wrapper.appendChild(bubble);
    elements.chatMessages.appendChild(wrapper);
  });
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
};

const loadPresets = async () => {
  const payload = await apiFetch('/api/presets');
  state.presets = payload.presets || [];
  renderPresets();
};

const loadSessions = async () => {
  const payload = await apiFetch('/api/chat/sessions');
  state.sessions = payload.sessions || [];
  if (!state.currentSessionId && state.sessions.length > 0) {
    state.currentSessionId = state.sessions[0].id;
  }
  renderChatSessions();
};

const loadSessionMessages = async (sessionId) => {
  const payload = await apiFetch(`/api/chat/sessions/${sessionId}`);
  const session = payload.session;
  if (!session) return;
  state.currentSessionId = session.id;
  if (elements.chatSessionId) elements.chatSessionId.value = session.id;
  if (elements.currentSessionBadge) elements.currentSessionBadge.textContent = `セッションID: ${session.id}`;
  renderChatMessages(session.messages || []);
  renderChatSessions();
};

const ensureChatReady = async () => {
  if (!state.user) return;
  await loadSessions();
  if (state.currentSessionId) {
    await loadSessionMessages(state.currentSessionId);
  }
};

const handleLogin = async (event) => {
  event.preventDefault();
  clearStatus();
  const username = elements.loginUsername?.value.trim() || '';
  const password = elements.loginPassword?.value || '';
  if (!username || !password) {
    showStatus('ユーザー名とパスワードを入力してください。', 'warning');
    return;
  }

  try {
    const payload = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    state.user = payload.user;
    await bootstrapAppData();
    renderApp();
  } catch (error) {
    showStatus(error.message || 'ログインに失敗しました。', 'danger');
  }
};

const handleLogout = async () => {
  try {
    await apiFetch('/api/auth/logout', { method: 'POST' });
  } catch (error) {
    showStatus(error.message || 'ログアウトに失敗しました。', 'warning');
  }
  setLoggedOut();
};

const handleGenerate = async (event) => {
  event.preventDefault();
  if (!elements.generateForm) return;
  toggleGenerationLoading(true);

  const modeId = elements.generationMode?.value || 'rough_with_instructions';
  let endpoint = '/api/generate/rough';
  if (modeId === 'reference_style_colorize') endpoint = '/api/generate/reference';
  if (modeId === 'inpaint_outpaint') endpoint = '/api/generate/edit';

  const formData = new FormData(elements.generateForm);

  try {
    const payload = await apiFetch(endpoint, {
      method: 'POST',
      body: formData,
      headers: {},
    });
    state.lastResult = payload.result;
    renderResult(state.lastResult);
    showStatus('生成が完了しました。', 'success');
  } catch (error) {
    showStatus(error.message || '生成に失敗しました。', 'danger');
  } finally {
    toggleGenerationLoading(false);
  }
};

const handlePresetSave = async (event) => {
  event.preventDefault();
  const payload = buildPresetPayload();
  if (!payload.name) {
    showStatus('プリセット名を入力してください。', 'warning');
    return;
  }

  try {
    const response = await apiFetch('/api/presets', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    state.presets.unshift(response.preset);
    renderPresets();
    if (elements.presetName) elements.presetName.value = '';
    showStatus('プリセットを保存しました。', 'success');
  } catch (error) {
    showStatus(error.message || 'プリセットの保存に失敗しました。', 'danger');
  }
};

const handlePresetDelete = async () => {
  const preset = findPreset();
  if (!preset) return;
  try {
    await apiFetch(`/api/presets/${preset.id}`, { method: 'DELETE' });
    state.presets = state.presets.filter((item) => item.id !== preset.id);
    renderPresets();
    showStatus('プリセットを削除しました。', 'info');
  } catch (error) {
    showStatus(error.message || 'プリセットの削除に失敗しました。', 'danger');
  }
};

const handleSignup = async (event) => {
  event.preventDefault();
  if (!state.user?.is_initial_user) {
    showStatus('初期ユーザーのみが新規登録できます。', 'warning');
    return;
  }

  const payload = {
    username: elements.signupUsername?.value.trim() || '',
    email: elements.signupEmail?.value.trim() || '',
    password: elements.signupPassword?.value || '',
  };

  if (!payload.username || !payload.email || !payload.password) {
    showStatus('すべての項目を入力してください。', 'warning');
    return;
  }

  try {
    await apiFetch('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    showStatus('ユーザーを作成しました。', 'success');
    if (elements.signupForm) elements.signupForm.reset();
  } catch (error) {
    showStatus(error.message || 'ユーザー作成に失敗しました。', 'danger');
  }
};

const handleNewSession = async () => {
  try {
    const payload = await apiFetch('/api/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({}),
    });
    const session = payload.session;
    state.sessions.unshift(session);
    state.currentSessionId = session.id;
    renderChatSessions();
    await loadSessionMessages(session.id);
  } catch (error) {
    showStatus(error.message || 'セッションの作成に失敗しました。', 'danger');
  }
};

const handleChatSubmit = async (event) => {
  event.preventDefault();
  if (!state.currentSessionId) {
    showStatus('チャットセッションを選択してください。', 'warning');
    return;
  }

  const selectedMode = elements.chatModeSelect?.value || 'text_chat';
  if (elements.chatStatus) elements.chatStatus.textContent = '送信中...';
  try {
    const formData = new FormData(elements.chatForm);
    formData.set('session_id', state.currentSessionId);

    await apiFetch('/api/chat/messages', {
      method: 'POST',
      body: formData,
      headers: {},
    });
    elements.chatForm.reset();
    if (elements.chatModeSelect) {
      elements.chatModeSelect.value = selectedMode;
    }
    toggleChatExtras(selectedMode);
    await loadSessions();
    await loadSessionMessages(state.currentSessionId);
    if (elements.chatStatus) elements.chatStatus.textContent = '';
  } catch (error) {
    if (elements.chatStatus) {
      elements.chatStatus.textContent = error.message || '送信に失敗しました。';
    }
  }
};

const bindEvents = () => {
  if (elements.loginForm) elements.loginForm.addEventListener('submit', handleLogin);
  if (elements.logoutButton) elements.logoutButton.addEventListener('click', handleLogout);

  if (elements.navViews) {
    elements.navViews.querySelectorAll('button[data-view]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const viewName = btn.dataset.view || 'generate';
        setView(viewName);
        window.location.hash = viewName;
      });
    });
  }

  if (elements.generationMode) {
    elements.generationMode.addEventListener('change', () => {
      updateModePanels(elements.generationMode.value);
    });
  }

  if (elements.generateForm) elements.generateForm.addEventListener('submit', handleGenerate);
  if (elements.applyPreset) elements.applyPreset.addEventListener('click', applyPreset);
  if (elements.deletePreset) elements.deletePreset.addEventListener('click', handlePresetDelete);
  if (elements.presetForm) elements.presetForm.addEventListener('submit', handlePresetSave);
  if (elements.newSessionButton) elements.newSessionButton.addEventListener('click', handleNewSession);

  if (elements.chatSessionList) {
    elements.chatSessionList.addEventListener('click', async (event) => {
      const target = event.target.closest('[data-session-id]');
      if (!target) return;
      const sessionId = Number(target.dataset.sessionId);
      if (!sessionId) return;
      await loadSessionMessages(sessionId);
    });
  }

  if (elements.chatModeSelect) {
    elements.chatModeSelect.addEventListener('change', () => {
      toggleChatExtras(elements.chatModeSelect.value);
    });
  }

  if (elements.chatForm) elements.chatForm.addEventListener('submit', handleChatSubmit);
  if (elements.signupForm) elements.signupForm.addEventListener('submit', handleSignup);

  window.addEventListener('hashchange', () => {
    const view = window.location.hash.replace('#', '');
    if (view === 'chat' || view === 'generate') {
      setView(view);
    }
  });
};

const bootstrapAppData = async () => {
  const [modesPayload, optionsPayload, chatModesPayload] = await Promise.all([
    apiFetch('/api/modes'),
    apiFetch('/api/options'),
    apiFetch('/api/chat/modes'),
  ]);

  state.modes = modesPayload.modes || [];
  state.options = optionsPayload;
  state.chatModes = chatModesPayload.modes || [];

  populateModes();
  populateOptions();
  populateChatModes();

  const defaultMode = state.modes.find((mode) => mode.id === 'rough_with_instructions')?.id || state.modes[0]?.id;
  if (elements.generationMode && defaultMode) {
    elements.generationMode.value = defaultMode;
    updateModePanels(defaultMode);
  }

  if (elements.chatModeSelect) {
    elements.chatModeSelect.value = state.chatModes[0]?.id || 'text_chat';
    toggleChatExtras(elements.chatModeSelect.value);
  }

  await loadPresets();
  renderResult(state.lastResult);

  const initialView = window.location.hash.replace('#', '') || 'generate';
  if (initialView === 'chat' || initialView === 'generate') {
    setView(initialView);
  }
};

const initApp = async () => {
  cacheElements();
  bindEvents();

  try {
    const payload = await apiFetch('/api/me');
    if (payload.authenticated) {
      state.user = payload.user;
      await bootstrapAppData();
      renderApp();
    } else {
      renderLogin();
    }
  } catch (error) {
    renderLogin();
  }
};

document.addEventListener('DOMContentLoaded', initApp);
