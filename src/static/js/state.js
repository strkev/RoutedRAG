// ==========================================================================
// STATE MANAGEMENT MODULE
// ==========================================================================

const State = {
  activeChatId: null,
  activeChat: null,
  chats: [],
  chatsTotal: 0,
  chatsOffset: 0,
  hasMoreChats: false,
  chatsLimit: 8,

  settings: {
    dynamic_model_enabled: true,
    active_personality: 'default',
    default_model: 'google/gemma-4-31b-it',
    custom_prompt: ''
  },

  personalities: [],
  rulesConfig: { default_model: 'google/gemma-4-31b-it', rules: [] },
  ragStatus: { folder_path: '', total_documents: 0, total_chunks: 0, files: [] },
  tools: [],
  isStreaming: false,

  listeners: {},

  on(event, callback) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(callback);
  },

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  },

  setSettings(newSettings) {
    this.settings = { ...this.settings, ...newSettings };
    this.emit('settingsChanged', this.settings);
  },

  setActiveChat(chat) {
    this.activeChat = chat;
    this.activeChatId = chat ? chat.id : null;
    this.emit('activeChatChanged', chat);
  },

  setChats(chats, total, hasMore, offset) {
    if (offset === 0) {
      this.chats = chats;
    } else {
      this.chats = [...this.chats, ...chats];
    }
    this.chatsTotal = total;
    this.hasMoreChats = hasMore;
    this.chatsOffset = offset;
    this.emit('chatsListChanged', { chats: this.chats, hasMore: this.hasMoreChats });
  }
};

window.State = State;
