// ==========================================================================
// ATOMIC DESIGN LEVEL 3: ORGANISM CONTROLLERS
// ==========================================================================

const Organisms = {
  // ------------------------------------------------------------------------
  // Sidebar & Chat History
  // ------------------------------------------------------------------------
  async initSidebar() {
    const dynamicSwitch = document.getElementById('sidebar-dynamic-toggle');
    if (dynamicSwitch) {
      dynamicSwitch.checked = State.settings.dynamic_model_enabled;
    }
    await this.loadChats(0);
  },

  async loadChats(offset = 0) {
    try {
      const data = await API.getChats(State.chatsLimit, offset);
      State.setChats(data.chats, data.total, data.has_more, offset);
      this.renderSidebarChats();
    } catch (e) {
      console.error('Error loading chats:', e);
    }
  },

  async loadMoreChats() {
    const nextOffset = State.chatsOffset + State.chatsLimit;
    await this.loadChats(nextOffset);
  },

  renderSidebarChats() {
    const container = document.getElementById('sidebar-chats-list');
    const showMoreBtn = document.getElementById('btn-show-more');
    if (!container) return;

    if (!State.chats || State.chats.length === 0) {
      container.innerHTML = '<div style="padding: 16px; font-size: 13px; color: var(--md-sys-color-on-surface-variant); text-align: center;">Noch keine Chats gespeichert</div>';
      if (showMoreBtn) showMoreBtn.style.display = 'none';
      return;
    }

    container.innerHTML = State.chats.map(chat => {
      const isActive = State.activeChatId === chat.id;
      return Molecules.renderSidebarItem(chat, isActive);
    }).join('');

    if (showMoreBtn) {
      showMoreBtn.style.display = State.hasMoreChats ? 'block' : 'none';
    }
  },

  async startNewChat() {
    if (State.isStreaming) return;
    try {
      localStorage.removeItem('routedrag_active_chat_id');
      history.replaceState(null, '', window.location.pathname);
    } catch (_) {}
    State.setActiveChat(null);
    ChatWindow.renderMessages();
    ChatWindow.updateHeader();
    ChatWindow.focusInput();
    this.renderSidebarChats();
  },

  async selectChat(chatId) {
    if (State.isStreaming) return;
    try {
      const chat = await API.getChat(chatId);
      State.setActiveChat(chat);
      try {
        localStorage.setItem('routedrag_active_chat_id', chatId);
        history.replaceState(null, '', '#' + chatId);
      } catch (_) {}

      if (chat.personality) {
        State.settings.active_personality = chat.personality;
      }
      if (chat.dynamic_model !== undefined) {
        State.settings.dynamic_model_enabled = chat.dynamic_model;
        const dynamicSwitch = document.getElementById('sidebar-dynamic-toggle');
        if (dynamicSwitch) dynamicSwitch.checked = chat.dynamic_model;
      }
      this.renderSidebarChats();
      ChatWindow.renderMessages();
      ChatWindow.updateHeader();
      // Mobile drawer auto-close
      document.querySelector('.sidebar')?.classList.remove('mobile-open');
    } catch (e) {
      console.error('Error selecting chat:', e);
      throw e;
    }
  },

  async promptRenameChat(chatId, currentTitle) {
    const newTitle = prompt('Chat umbenennen:', currentTitle);
    if (newTitle && newTitle.trim() && newTitle !== currentTitle) {
      try {
        await API.renameChat(chatId, newTitle.trim());
        if (State.activeChat && State.activeChat.id === chatId) {
          State.activeChat.title = newTitle.trim();
          ChatWindow.updateHeader();
        }
        await this.loadChats(0);
      } catch (e) {
        alert('Fehler beim Umbenennen: ' + e.message);
      }
    }
  },

  async confirmDeleteChat(chatId) {
    if (confirm('Möchtest du diesen Chat wirklich löschen?')) {
      try {
        await API.deleteChat(chatId);
        if (State.activeChatId === chatId) {
          this.startNewChat();
        }
        await this.loadChats(0);
      } catch (e) {
        alert('Fehler beim Löschen: ' + e.message);
      }
    }
  },

  async toggleDynamicModel(enabled) {
    State.settings.dynamic_model_enabled = enabled;
    const dynamicSwitch = document.getElementById('sidebar-dynamic-toggle');
    if (dynamicSwitch) dynamicSwitch.checked = enabled;

    try {
      await API.saveSettings(State.settings);
      ChatWindow.updateHeader();
    } catch (e) {
      console.error('Error saving dynamic model toggle:', e);
    }
  },

  // ------------------------------------------------------------------------
  // Settings Modal & Personalities
  // ------------------------------------------------------------------------
  async openSettingsModal() {
    try {
      const [settings, personas] = await Promise.all([
        API.getSettings(),
        API.getPersonalities()
      ]);
      State.settings = settings;
      State.personalities = personas;

      this.renderPersonalitiesGrid();

      const defaultModelInput = document.getElementById('settings-default-model');
      if (defaultModelInput) defaultModelInput.value = settings.default_model || '';

      const customPromptArea = document.getElementById('settings-custom-prompt');
      if (customPromptArea) customPromptArea.value = settings.custom_prompt || '';

      const customContainer = document.getElementById('custom-prompt-container');
      if (customContainer) {
        customContainer.style.display = settings.active_personality === 'custom' ? 'block' : 'none';
      }

      this.openModal('settings-modal');
    } catch (e) {
      console.error('Error loading settings:', e);
    }
  },

  renderPersonalitiesGrid() {
    const grid = document.getElementById('personalities-grid');
    if (!grid) return;

    grid.innerHTML = State.personalities.map(p => {
      const isSelected = p.id === State.settings.active_personality;
      return Molecules.renderPersonalityCard(p, isSelected);
    }).join('');
  },

  selectPersonality(personaId) {
    State.settings.active_personality = personaId;
    this.renderPersonalitiesGrid();
    const customContainer = document.getElementById('custom-prompt-container');
    if (customContainer) {
      customContainer.style.display = personaId === 'custom' ? 'block' : 'none';
    }
  },

  async saveSettings() {
    const defaultModel = document.getElementById('settings-default-model').value.trim();
    const customPrompt = document.getElementById('settings-custom-prompt').value.trim();

    State.settings.default_model = defaultModel;
    State.settings.custom_prompt = customPrompt;

    try {
      await API.saveSettings(State.settings);
      this.closeModal('settings-modal');
      ChatWindow.updateHeader();
    } catch (e) {
      alert('Fehler beim Speichern der Einstellungen: ' + e.message);
    }
  },

  // ------------------------------------------------------------------------
  // Rules Editor Modal (Themen- & Keyword-Routing)
  // ------------------------------------------------------------------------
  async openRulesEditorModal() {
    try {
      const [rulesConfig, connsData] = await Promise.all([
        API.getRules(),
        API.getConnections()
      ]);
      State.rulesConfig = rulesConfig;
      State.connectionsData = connsData;

      const fallbackConnSelect = document.getElementById('rules-fallback-connection');
      if (fallbackConnSelect && connsData.connections) {
        fallbackConnSelect.innerHTML = connsData.connections.map(c => {
          const isSel = (rulesConfig.default_connection === c.id) ? 'selected' : '';
          return `<option value="${c.id}" ${isSel}>${Atoms.escapeHtml(c.name || c.id)}</option>`;
        }).join('');
      }

      const fallbackInput = document.getElementById('rules-fallback-model');
      if (fallbackInput) fallbackInput.value = rulesConfig.default_model || '';

      this.renderRulesList();
      this.openModal('rules-modal');
    } catch (e) {
      console.error('Error loading rules:', e);
    }
  },

  renderRulesList() {
    const list = document.getElementById('rules-list');
    if (!list) return;

    const conns = State.connectionsData ? State.connectionsData.connections : [];

    if (!State.rulesConfig.rules || State.rulesConfig.rules.length === 0) {
      list.innerHTML = '<div style="padding: 16px; color: var(--md-sys-color-on-surface-variant); text-align: center;">Keine Themen-Regeln definiert. Klicke auf „+ Regel hinzufügen“.</div>';
      return;
    }

    list.innerHTML = State.rulesConfig.rules.map((rule, idx) => {
      return Molecules.renderRuleCard(rule, idx, conns);
    }).join('');
  },

  updateRuleField(index, field, value) {
    if (State.rulesConfig.rules[index]) {
      State.rulesConfig.rules[index][field] = value;
    }
  },

  updateRuleKeywords(index, rawValue) {
    if (State.rulesConfig.rules[index]) {
      const keywords = rawValue.split(',').map(s => s.trim()).filter(Boolean);
      State.rulesConfig.rules[index].keywords = keywords;
    }
  },

  addNewRule() {
    const conns = State.connectionsData ? State.connectionsData.connections : [];
    const defConn = State.rulesConfig.default_connection || (conns[0] ? conns[0].id : 'uni');
    const newRule = {
      id: 'rule_' + Date.now(),
      name: 'Neues Thema',
      keywords: ['stichwort'],
      target_connection: defConn,
      target_model: State.rulesConfig.default_model || 'google/gemma-4-31b-it',
      active: true
    };
    State.rulesConfig.rules.push(newRule);
    this.renderRulesList();
  },

  deleteRule(index) {
    if (confirm('Regel löschen?')) {
      State.rulesConfig.rules.splice(index, 1);
      this.renderRulesList();
    }
  },

  async saveRules() {
    const fallbackModel = document.getElementById('rules-fallback-model').value.trim();
    const fallbackConnSelect = document.getElementById('rules-fallback-connection');
    
    State.rulesConfig.default_model = fallbackModel;
    if (fallbackConnSelect) {
      State.rulesConfig.default_connection = fallbackConnSelect.value;
    }

    try {
      await API.saveRules(State.rulesConfig);
      this.closeModal('rules-modal');
    } catch (e) {
      alert('Fehler beim Speichern der Regeln: ' + e.message);
    }
  },

  // ------------------------------------------------------------------------
  // Connections Modal (Multi-Provider)
  // ------------------------------------------------------------------------
  async openConnectionsModal() {
    try {
      const data = await API.getConnections();
      State.connectionsData = data;
      this.renderConnectionsList();
      this.openModal('connections-modal');
    } catch (e) {
      console.error('Error loading connections:', e);
    }
  },

  renderConnectionsList() {
    const list = document.getElementById('connections-list');
    if (!list) return;
    const conns = (State.connectionsData && State.connectionsData.connections) ? State.connectionsData.connections : [];
    const defId = State.connectionsData ? (State.connectionsData.default_connection || (conns[0] ? conns[0].id : '')) : '';

    if (conns.length === 0) {
      list.innerHTML = '<div style="padding: 16px; color: var(--md-sys-color-on-surface-variant); text-align: center;">Keine Verbindungen vorhanden. Klicke auf „+ Verbindung hinzufügen“.</div>';
      return;
    }

    list.innerHTML = conns.map((conn, idx) => {
      const isDefault = conn.id === defId;
      return Molecules.renderConnectionCard(conn, isDefault, idx);
    }).join('');
  },

  addNewConnection() {
    if (!State.connectionsData) State.connectionsData = { default_connection: 'conn_1', connections: [] };
    const newId = 'conn_' + Date.now();
    State.connectionsData.connections.push({
      id: newId,
      name: 'Neuer Provider',
      base_url: 'http://localhost:11434/v1',
      api_key: '',
      default_model: 'llama3.2:latest'
    });
    if (!State.connectionsData.default_connection) {
      State.connectionsData.default_connection = newId;
    }
    this.renderConnectionsList();
  },

  updateConnectionField(index, field, value) {
    if (State.connectionsData.connections[index]) {
      State.connectionsData.connections[index][field] = value;
    }
  },

  setDefaultConnection(connId) {
    if (State.connectionsData) {
      State.connectionsData.default_connection = connId;
      this.renderConnectionsList();
    }
  },

  deleteConnection(index) {
    const conns = State.connectionsData.connections;
    if (conns.length <= 1) {
      alert('Mindestens eine Verbindung muss erhalten bleiben.');
      return;
    }
    if (confirm('Möchtest du diese Verbindung wirklich löschen?')) {
      const deletedId = conns[index].id;
      conns.splice(index, 1);
      if (State.connectionsData.default_connection === deletedId) {
        State.connectionsData.default_connection = conns[0].id;
      }
      this.renderConnectionsList();
    }
  },

  toggleCardKeyVisibility(index) {
    const input = document.getElementById(`conn-card-key-${index}`);
    const eye = document.getElementById(`conn-eye-${index}`);
    if (!input || !eye) return;
    if (input.type === 'password') {
      input.type = 'text';
      eye.innerText = 'visibility_off';
    } else {
      input.type = 'password';
      eye.innerText = 'visibility';
    }
  },

  async testSingleConnection(index) {
    const conn = State.connectionsData.connections[index];
    if (!conn) return;
    const testResult = document.getElementById(`conn-test-result-${index}`);
    if (testResult) testResult.innerHTML = '<span class="badge">Prüfe...</span>';

    try {
      const res = await API.testConnection(conn);
      if (res.status === 'success') {
        const modelCount = res.models ? res.models.length : 0;
        const modelList = res.models && res.models.length > 0 ? ` (${res.models.slice(0, 3).join(', ')}${res.models.length > 3 ? '...' : ''})` : '';
        testResult.innerHTML = Atoms.renderBadge(`Erreichbar! (${modelCount} Modelle)${modelList}`, 'success', 'check_circle');
      } else if (res.status === 'warning') {
        testResult.innerHTML = Atoms.renderBadge(`Erreicht (HTTP ${res.status_code})`, 'warning', 'info');
      } else {
        testResult.innerHTML = Atoms.renderBadge(`Fehler: ${res.error}`, 'error', 'cancel');
      }
    } catch (e) {
      testResult.innerHTML = Atoms.renderBadge(`Fehler: ${e.message}`, 'error', 'cancel');
    }
  },

  async saveConnections() {
    try {
      await API.saveConnections(State.connectionsData);
      this.closeModal('connections-modal');
    } catch (e) {
      alert('Fehler beim Speichern: ' + e.message);
    }
  },

  // ------------------------------------------------------------------------
  // RAG Resources Modal
  // ------------------------------------------------------------------------
  async openRagModal() {
    try {
      const status = await API.getRagStatus();
      State.ragStatus = status;

      document.getElementById('rag-folder-path').value = status.folder_path || '';
      document.getElementById('rag-total-docs').innerText = status.total_documents || '0';
      document.getElementById('rag-total-chunks').innerText = status.total_chunks || '0';
      
      const filesList = document.getElementById('rag-files-list');
      if (filesList) {
        if (status.files && status.files.length > 0) {
          filesList.innerHTML = status.files.map(f => `<li><code>${Atoms.escapeHtml(f)}</code></li>`).join('');
        } else {
          filesList.innerHTML = '<li><em>Keine Dokumente gefunden</em></li>';
        }
      }

      this.openModal('rag-modal');
    } catch (e) {
      console.error('Error loading RAG status:', e);
    }
  },

  async updateRagFolder() {
    const folder = document.getElementById('rag-folder-path').value.trim();
    if (!folder) return;

    try {
      const res = await API.updateRagFolder(folder);
      await this.openRagModal();
    } catch (e) {
      alert('Fehler beim Ändern des Ordners: ' + e.message);
    }
  },

  async reindexRag() {
    const btn = document.getElementById('btn-reindex-rag');
    if (btn) btn.innerText = 'Indiziere...';

    try {
      await API.reindexRag();
      await this.openRagModal();
    } catch (e) {
      alert('Fehler bei der Re-Indizierung: ' + e.message);
    } finally {
      if (btn) btn.innerText = 'Neu indizieren';
    }
  },

  async handleFileUpload(file) {
    if (!file) return;
    try {
      await API.uploadRagFile(file);
      await this.openRagModal();
    } catch (e) {
      alert('Fehler beim Hochladen: ' + e.message);
    }
  },

  // ------------------------------------------------------------------------
  // Modal Utils
  // ------------------------------------------------------------------------
  openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.add('active');
  },

  closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.remove('active');
  }
};

window.Organisms = Organisms;
