const initChatModeMenu = () => {
  const modeInput = document.getElementById('chatModeInput');
  const modeLabel = document.getElementById('chatModeLabel');
  const modeHelper = document.getElementById('chatModeHelper');
  const modeButtons = document.querySelectorAll('[data-mode-id]');

  if (!modeInput || modeButtons.length === 0) return null;

  const splitModes = (raw) =>
    String(raw || '')
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);

  const toggleVisibility = (modeId) => {
    document.querySelectorAll('[data-mode-visible]').forEach((el) => {
      const modes = splitModes(el.dataset.modeVisible);
      const shouldShow = modes.includes(modeId);
      el.classList.toggle('d-none', !shouldShow);
    });
  };

  const applyMode = (modeId, label, helper) => {
    modeInput.value = modeId;
    if (modeLabel) modeLabel.textContent = label;
    if (modeHelper) modeHelper.textContent = helper;
    toggleVisibility(modeId);
  };

  modeButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const modeId = button.dataset.modeId;
      const label = button.dataset.modeLabel || 'テキストチャット';
      const helper = button.dataset.modeHelper || '';
      applyMode(modeId, label, helper);
    });
  });

  applyMode(modeInput.value, modeLabel?.textContent || 'テキストチャット', modeHelper?.textContent || '');
  return { applyMode };
};

const buildMessageElement = (message) => {
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
  return wrapper;
};

const buildUserAttachments = (form, modeId) => {
  const attachments = [];
  const addFile = (inputName, kind) => {
    const input = form.querySelector(`input[name="${inputName}"]`);
    if (!input || !input.files || input.files.length === 0) return;
    const file = input.files[0];
    attachments.push({ kind, url: URL.createObjectURL(file) });
  };

  if (modeId === 'rough_with_instructions') {
    addFile('rough_image', 'rough');
  } else if (modeId === 'reference_style_colorize') {
    addFile('reference_image', 'reference');
    addFile('rough_image', 'rough');
  } else if (modeId === 'inpaint_outpaint') {
    addFile('edit_base_image', 'base');
    addFile('edit_mask_image', 'mask');
  }

  return attachments;
};

const buildUserText = (form, modeId) => {
  const message = form.querySelector('textarea[name="message"]')?.value || '';
  if (modeId === 'rough_with_instructions') {
    const color = form.querySelector('textarea[name="color_instruction"]')?.value || '';
    const pose = form.querySelector('textarea[name="pose_instruction"]')?.value || '';
    return `色: ${color}\nポーズ: ${pose}`.trim();
  }
  if (modeId === 'reference_style_colorize') {
    return '完成絵参照→ラフ着色を依頼';
  }
  if (modeId === 'inpaint_outpaint') {
    const editInstruction = form.querySelector('textarea[name="edit_instruction"]')?.value || '';
    return editInstruction || 'マスク編集を依頼';
  }
  return message;
};

const initChatForm = (modeController) => {
  const form = document.getElementById('chatForm');
  const messages = document.getElementById('chatMessages');
  const submitButton = document.getElementById('chatSubmit');
  const status = document.getElementById('chatStatus');
  if (!form || !messages || !submitButton) return;

  const endpoint = form.dataset.endpoint || '/chat/messages';

  const scrollToBottom = () => {
    messages.scrollTop = messages.scrollHeight;
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const modeId = formData.get('mode_id');
    const messageText = buildUserText(form, modeId);

    submitButton.disabled = true;
    if (status) status.textContent = '送信中...';

    const userMessage = {
      role: 'user',
      mode_id: modeId,
      text: messageText,
      attachments: buildUserAttachments(form, modeId),
    };

    const emptyState = messages.querySelector('.empty-chat');
    if (emptyState) emptyState.remove();
    const userElement = buildMessageElement(userMessage);
    messages.appendChild(userElement);
    scrollToBottom();

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || '送信に失敗しました。');
      }
      if (payload.assistant) {
        messages.appendChild(buildMessageElement(payload.assistant));
      }
      form.reset();
      if (modeController && typeof modeController.applyMode === 'function') {
        const currentLabel = document.getElementById('chatModeLabel')?.textContent || 'テキストチャット';
        const currentHelper = document.getElementById('chatModeHelper')?.textContent || '';
        modeController.applyMode(modeId, currentLabel, currentHelper);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '送信に失敗しました。';
      if (status) status.textContent = errorMessage;
      if (userElement) userElement.remove();
    } finally {
      submitButton.disabled = false;
      if (status && status.textContent === '送信中...') status.textContent = '';
      scrollToBottom();
    }
  });
};

const bootstrapChatPage = () => {
  const modeController = initChatModeMenu();
  initChatForm(modeController);
};

document.addEventListener('DOMContentLoaded', bootstrapChatPage);
