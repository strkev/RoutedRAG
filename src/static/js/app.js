// ==========================================================================
// MASTER APP CONTROLLER & CHAT WINDOW
// ==========================================================================

const ChatWindow = {
  init() {
    this.messagesArea = document.getElementById('messages-scroll-area');
    this.textarea = document.getElementById('chat-input-textarea');
    this.sendBtn = document.getElementById('btn-send-message');

    // Auto-resize textarea
    this.textarea.addEventListener('input', () => {
      this.textarea.style.height = 'auto';
      this.textarea.style.height = Math.min(this.textarea.scrollHeight, 180) + 'px';
      this.sendBtn.disabled = !this.textarea.value.trim();
    });

    // Enter to send (Shift+Enter for newline)
    this.textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (this.textarea.value.trim() && !State.isStreaming) {
          this.sendMessage();
        }
      }
    });

    this.sendBtn.addEventListener('click', () => {
      if (this.textarea.value.trim() && !State.isStreaming) {
        this.sendMessage();
      }
    });

    this.renderMessages();
    this.updateHeader();
  },

  focusInput() {
    if (this.textarea) this.textarea.focus();
  },

  updateHeader() {
    const titleEl = document.getElementById('chat-header-title');
    const badgesEl = document.getElementById('chat-header-badges');

    if (titleEl) {
      titleEl.innerText = State.activeChat ? State.activeChat.title : 'Neuer Chat';
    }

    if (badgesEl) {
      const persona = State.settings.active_personality || 'default';
      const personaBadge = Atoms.renderBadge(`Persona: ${persona}`, 'primary', 'psychology');

      badgesEl.innerHTML = `${personaBadge}`;
    }
  },

  renderMessages() {
    if (!this.messagesArea) return;

    if (!State.activeChat || !State.activeChat.messages || State.activeChat.messages.length === 0) {
      this.messagesArea.innerHTML = `
        <div class="empty-chat-welcome">
          <div class="welcome-title">Was kann ich für dich tun?</div>
          <div class="welcome-subtitle">
            Ausgestattet mit dynamischem Model-Routing, lokaler RAG-Wissensdatenbank und erweiterbaren Agenten-Tools.
          </div>
          <div class="welcome-suggestions">
            <button class="chip" onclick="ChatWindow.sendPrompt('Wie ist das Wetter aktuell in Oberursel?')">
              ${Atoms.renderIcon('cloud')} Wie ist das Wetter in Oberursel?
            </button>
            <button class="chip" onclick="ChatWindow.sendPrompt('Was weißt du über Apple und MacBooks?')">
              ${Atoms.renderIcon('menu_book')} Was weißt du über Apple & MacBooks?
            </button>
            <button class="chip" onclick="ChatWindow.sendPrompt('Schreibe mir eine Python-Funktion für einen Binary Search.')">
              ${Atoms.renderIcon('code')} Schreibe mir eine Python-Funktion
            </button>
            <button class="chip" onclick="ChatWindow.sendPrompt('Wo befinde ich mich gerade?')">
              ${Atoms.renderIcon('location_on')} Wo befinde ich mich?
            </button>
          </div>
        </div>
      `;
      return;
    }

    this.messagesArea.innerHTML = State.activeChat.messages.map(msg => {
      return Molecules.renderMessageBubble(msg);
    }).join('');

    this.scrollToBottom();
  },

  sendPrompt(text) {
    if (this.textarea) {
      this.textarea.value = text;
      this.textarea.style.height = 'auto';
      this.sendBtn.disabled = false;
      this.sendMessage();
    }
  },

  scrollToBottom() {
    if (this.messagesArea) {
      this.messagesArea.scrollTop = this.messagesArea.scrollHeight;
    }
  },

  async sendMessage() {
    const text = this.textarea.value.trim();
    if (!text || State.isStreaming) return;

    this.textarea.value = '';
    this.textarea.style.height = 'auto';
    this.sendBtn.disabled = true;
    State.isStreaming = true;

    // Active or new chat
    let chatId = State.activeChatId;
    if (!chatId) {
      chatId = 'chat_' + Date.now();
      State.activeChat = {
        id: chatId,
        title: text.substring(0, 32) + (text.length > 32 ? '...' : ''),
        personality: State.settings.active_personality,
        dynamic_model: State.settings.dynamic_model_enabled,
        messages: []
      };
      State.activeChatId = chatId;
      try {
        localStorage.setItem('routedrag_active_chat_id', chatId);
        history.replaceState(null, '', '#' + chatId);
      } catch (_) {}
    }

    // Add user message to UI
    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    };
    State.activeChat.messages.push(userMsg);
    this.renderMessages();

    // Prepare assistant placeholder bubble
    const assistantMsgId = 'assistant_' + Date.now();
    const assistantBubbleWrapper = document.createElement('div');
    assistantBubbleWrapper.id = assistantMsgId;
    assistantBubbleWrapper.innerHTML = `
      <div class="message-row assistant-row">
        ${Atoms.renderAvatar('ai')}
        <div class="message-content-wrap">
          <div class="message-header">
            <span>Assistent</span>
          </div>
          <div class="message-body" id="body-${assistantMsgId}">
            <span class="typing-indicator">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
            </span>
          </div>
          <div class="message-footer" id="footer-${assistantMsgId}"></div>
        </div>
      </div>
    `;
    this.messagesArea.appendChild(assistantBubbleWrapper);
    this.scrollToBottom();

    let accumulatedContent = '';
    let toolCalls = [];
    let chosenModel = '';

    const payload = {
      message: text,
      chat_id: chatId,
      personality: State.settings.active_personality,
      dynamic_model: State.settings.dynamic_model_enabled,
      selected_model: State.settings.default_model,
      custom_prompt: State.settings.custom_prompt
    };

    const bodyEl = document.getElementById(`body-${assistantMsgId}`);
    const footerEl = document.getElementById(`footer-${assistantMsgId}`);

    API.streamMessage(payload, {
      onInit: (data) => {
        if (!State.activeChatId) {
          State.activeChatId = data.chat_id;
        }
        if (State.activeChat && (!State.activeChat.id || State.activeChat.id !== data.chat_id)) {
          State.activeChat.id = data.chat_id;
          State.activeChatId = data.chat_id;
        }
        try {
          localStorage.setItem('routedrag_active_chat_id', data.chat_id);
          history.replaceState(null, '', '#' + data.chat_id);
        } catch (_) {}
      },
      onToken: (token) => {
        accumulatedContent += token;
        if (bodyEl) {
          bodyEl.innerHTML = Molecules.parseMarkdown(accumulatedContent);
        }
        ChatWindow.scrollToBottom();
      },
      onTool: (tool) => {
        toolCalls.push(tool);
        if (footerEl) {
          footerEl.innerHTML = `<span style="font-size: 11.5px; color: var(--md-sys-color-primary); display: inline-flex; align-items: center; gap: 4px;">${Atoms.renderIcon('build')} <span>Tool: ${Atoms.escapeHtml(tool.name)}...</span></span>`;
        }
      },
      onDone: async (data) => {
        chosenModel = data.model_used;
        const tokenUsage = data.token_usage;

        if (footerEl) {
          footerEl.innerHTML = Molecules.renderMetaDetails(chosenModel, toolCalls, tokenUsage);
        }

        // Save complete message to state if still on this chat
        if (State.activeChat && State.activeChat.id === chatId) {
          State.activeChat.messages.push({
            id: assistantMsgId,
            role: 'assistant',
            content: accumulatedContent,
            model_used: chosenModel,
            tool_calls: toolCalls,
            token_usage: tokenUsage,
            created_at: new Date().toISOString()
          });
        }

        State.isStreaming = false;
        await Organisms.loadChats(0);
        if (State.activeChat && State.activeChat.id === chatId) {
          const updatedChat = State.chats.find(c => c.id === chatId);
          if (updatedChat) {
            State.activeChat.title = updatedChat.title;
          }
          ChatWindow.updateHeader();
        }
      },
      onError: (err) => {
        console.error('Streaming error:', err);
        if (bodyEl) {
          bodyEl.innerHTML += `<br><span style="color: var(--md-sys-color-error);">Fehler: ${Atoms.escapeHtml(err.toString())}</span>`;
        }
        State.isStreaming = false;
      }
    });
  }
};

// Global App Initialization
document.addEventListener('DOMContentLoaded', async () => {
  try {
    // Load initial settings
    const [settings, personas] = await Promise.all([
      API.getSettings(),
      API.getPersonalities()
    ]);
    State.settings = settings;
    State.personalities = personas;

    // Init Sidebar & ChatWindow
    await Organisms.initSidebar();
    ChatWindow.init();

    // Restore active chat if page was refreshed
    const targetChatId = window.location.hash.replace('#', '') || localStorage.getItem('routedrag_active_chat_id');
    if (targetChatId) {
      try {
        await Organisms.selectChat(targetChatId);
      } catch (err) {
        console.warn('Could not restore previous chat session:', err);
        localStorage.removeItem('routedrag_active_chat_id');
        try {
          history.replaceState(null, '', window.location.pathname);
        } catch (_) {}
      }
    }

    // Setup Mobile menu toggle
    const mobileBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.querySelector('.sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    if (mobileBtn && sidebar) {
      mobileBtn.addEventListener('click', () => {
        sidebar.classList.toggle('mobile-open');
      });
    }
    if (backdrop && sidebar) {
      backdrop.addEventListener('click', () => {
        sidebar.classList.remove('mobile-open');
      });
    }

    // Drag and drop for RAG files
    const dropzone = document.getElementById('rag-dropzone');
    const fileInput = document.getElementById('rag-file-input');
    if (dropzone && fileInput) {
      dropzone.addEventListener('click', () => fileInput.click());
      dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--md-sys-color-primary)';
      });
      dropzone.addEventListener('dragleave', () => {
        dropzone.style.borderColor = 'var(--md-sys-color-outline)';
      });
      dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--md-sys-color-outline)';
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          Organisms.handleFileUpload(e.dataTransfer.files[0]);
        }
      });
      fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          Organisms.handleFileUpload(e.target.files[0]);
        }
      });
    }

    // Escape key closes modals
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
      }
    });

  } catch (e) {
    console.error('App init failed:', e);
  }
});

window.ChatWindow = ChatWindow;
