// ==========================================================================
// API CLIENT MODULE
// ==========================================================================

const API = {
  // Chats
  async getChats(limit = 10, offset = 0) {
    const res = await fetch(`/api/chats?limit=${limit}&offset=${offset}`);
    if (!res.ok) throw new Error('Failed to load chats');
    return res.json();
  },

  async getChat(chatId) {
    const res = await fetch(`/api/chats/${chatId}`);
    if (!res.ok) throw new Error('Failed to load chat');
    return res.json();
  },

  async createChat(title = 'Neuer Chat', personality = 'default', dynamicModel = true) {
    const res = await fetch('/api/chats', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, personality, dynamic_model: dynamicModel })
    });
    if (!res.ok) throw new Error('Failed to create chat');
    return res.json();
  },

  async renameChat(chatId, title) {
    const res = await fetch(`/api/chats/${chatId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title })
    });
    if (!res.ok) throw new Error('Failed to rename chat');
    return res.json();
  },

  async deleteChat(chatId) {
    const res = await fetch(`/api/chats/${chatId}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Failed to delete chat');
    return res.json();
  },

  // Chat Execution
  async sendMessage(payload) {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Chat request failed');
    return res.json();
  },

  streamMessage(payload, { onInit, onToken, onTool, onDone, onError }) {
    fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(response => {
      if (!response.ok) throw new Error(`HTTP error ${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      function read() {
        reader.read().then(({ done, value }) => {
          if (done) return;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop(); // keep partial chunk

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6));
                if (data.event === 'init' && onInit) onInit(data);
                else if (data.event === 'token' && onToken) onToken(data.token);
                else if (data.event === 'tool_call' && onTool) onTool(data.tool);
                else if (data.event === 'done' && onDone) onDone(data);
                else if (data.event === 'error' && onError) onError(data.error);
              } catch (e) {
                console.error('Error parsing SSE data:', e, line);
              }
            }
          }
          read();
        }).catch(err => {
          if (onError) onError(err);
        });
      }
      read();
    }).catch(err => {
      if (onError) onError(err);
    });
  },

  // Settings & Personalities
  async getSettings() {
    const res = await fetch('/api/settings');
    return res.json();
  },

  async saveSettings(settings) {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    });
    return res.json();
  },

  async getPersonalities() {
    const res = await fetch('/api/personalities');
    return res.json();
  },

  // Rules Editor
  async getRules() {
    const res = await fetch('/api/rules');
    return res.json();
  },

  async saveRules(rulesConfig) {
    const res = await fetch('/api/rules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rulesConfig)
    });
    return res.json();
  },

  // Connections
  async getConnections() {
    const res = await fetch('/api/connections');
    return res.json();
  },

  async saveConnections(conn) {
    const res = await fetch('/api/connections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(conn)
    });
    return res.json();
  },

  async testConnection(conn) {
    const res = await fetch('/api/connections/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(conn)
    });
    return res.json();
  },

  // RAG Resources
  async getRagStatus() {
    const res = await fetch('/api/rag/status');
    return res.json();
  },

  async updateRagFolder(folderPath) {
    const res = await fetch('/api/rag/folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: folderPath })
    });
    return res.json();
  },

  async reindexRag() {
    const res = await fetch('/api/rag/reindex', {
      method: 'POST'
    });
    return res.json();
  },

  async uploadRagFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/rag/upload', {
      method: 'POST',
      body: formData
    });
    return res.json();
  },

  // Tools
  async getTools() {
    const res = await fetch('/api/tools');
    return res.json();
  }
};

window.API = API;
