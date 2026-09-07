// ==========================================================================
// ATOMIC DESIGN LEVEL 2: MOLECULE RENDERERS
// ==========================================================================

const Molecules = {
  parseMarkdown(text) {
    if (!text) return '';
    let html = Atoms.escapeHtml(text);

    // 1. Extract fenced Code Blocks into placeholders to prevent newline/markdown conversion
    const codeBlocks = [];
    html = html.replace(/```([a-zA-Z0-9_-]*)\n?([\s\S]*?)```/g, (match, lang, code) => {
      const language = (lang || 'code').trim();
      const cleanCode = code.replace(/\n+$/, '');
      const placeholder = `___CODEBLOCK_${codeBlocks.length}___`;
      const blockHtml = `<div class="code-block-container"><div class="code-block-header"><span>${language}</span><button class="btn btn-text" style="height: 24px; padding: 0 8px; font-size: 11px;" onclick="Molecules.copyCode(this)">Kopieren</button></div><pre><code>${cleanCode}</code></pre></div>`;
      codeBlocks.push(blockHtml);
      return `\n\n${placeholder}\n\n`;
    });

    // 2. Extract Inline Code into placeholders
    const inlineCodes = [];
    html = html.replace(/`([^`]+)`/g, (match, code) => {
      const placeholder = `___INLINECODE_${inlineCodes.length}___`;
      inlineCodes.push(`<code>${code}</code>`);
      return placeholder;
    });

    // 3. Headers
    html = html.replace(/^### (.*$)/gim, '<h3 style="font-size: 16px; margin: 12px 0 6px 0; color: var(--md-sys-color-primary); font-weight: 600;">$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2 style="font-size: 18px; margin: 14px 0 8px 0; color: var(--md-sys-color-on-surface); font-weight: 600;">$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1 style="font-size: 20px; margin: 16px 0 10px 0; color: var(--md-sys-color-on-surface); font-weight: 600;">$1</h1>');

    // 4. Bold & Italics
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 5. Unordered lists
    html = html.replace(/^\s*-\s+(.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
    html = html.replace(/<\/ul>\s*<ul>/g, '');

    // 6. Paragraph breaks
    html = html.replace(/\n\s*\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    html = `<p>${html}</p>`;

    // 7. Clean up empty tags and invalid block nesting
    html = html.replace(/<p>\s*<\/p>/g, '');
    html = html.replace(/<p>\s*<br\s*\/?>\s*/gi, '<p>');
    html = html.replace(/<br\s*\/?>\s*<\/p>/gi, '</p>');
    html = html.replace(/<p>\s*(<h[1-6][^>]*>[\s\S]*?<\/h[1-6]>)\s*<\/p>/gi, '$1');
    html = html.replace(/<p>\s*(<ul>[\s\S]*?<\/ul>)\s*<\/p>/gi, '$1');

    // 8. Re-insert Code Blocks (stripping enclosing <p> wrapper if any)
    codeBlocks.forEach((block, i) => {
      const placeholder = `___CODEBLOCK_${i}___`;
      const pWrapperRegex = new RegExp(`<p>\\s*(?:<br\\s*\\/?>)?\\s*${placeholder}\\s*(?:<br\\s*\\/?>)?\\s*<\\/p>`, 'g');
      if (pWrapperRegex.test(html)) {
        html = html.replace(pWrapperRegex, block);
      } else {
        html = html.replace(placeholder, block);
      }
    });

    // 9. Re-insert Inline Codes
    inlineCodes.forEach((code, i) => {
      html = html.replace(`___INLINECODE_${i}___`, code);
    });

    return html;
  },

  copyCode(btn) {
    const pre = btn.closest('.code-block-container').querySelector('pre code');
    if (pre) {
      navigator.clipboard.writeText(pre.innerText).then(() => {
        const orig = btn.innerText;
        btn.innerText = 'Kopiert!';
        setTimeout(() => btn.innerText = orig, 1500);
      });
    }
  },

  renderMetaDetails(modelUsed, toolCalls, tokenUsage) {
    if (!modelUsed && (!toolCalls || toolCalls.length === 0) && !tokenUsage) {
      return '';
    }

    let rows = '';

    // 1. Model
    if (modelUsed) {
      rows += `
        <div class="meta-detail-row">
          <span class="meta-detail-label">Model:</span>
          <span class="meta-detail-value"><code>${Atoms.escapeHtml(modelUsed)}</code></span>
        </div>
      `;
    }

    // 2. Tools
    if (toolCalls && toolCalls.length > 0) {
      const toolNames = toolCalls.map(tc => tc.name || 'tool').join(', ');
      rows += `
        <div class="meta-detail-row">
          <span class="meta-detail-label">Tools:</span>
          <span class="meta-detail-value"><code>${Atoms.escapeHtml(toolNames)}</code></span>
        </div>
      `;
    }

    // 3. Tokens
    if (tokenUsage) {
      const usage = typeof tokenUsage === 'string' ? JSON.parse(tokenUsage) : tokenUsage;
      if (usage && usage.total_tokens !== undefined) {
        rows += `
          <div class="meta-detail-row">
            <span class="meta-detail-label">Tokens:</span>
            <span class="meta-detail-value">
              <strong>${usage.total_tokens}</strong> (Input: ${usage.prompt_tokens || 0}, Output: ${usage.completion_tokens || 0})
            </span>
          </div>
        `;
      }
    }

    return `
      <details class="message-meta-details">
        <summary class="meta-details-summary">
          ${Atoms.renderIcon('expand_more', 'expand-icon')}
          <span>Details</span>
        </summary>
        <div class="meta-details-body">
          ${rows}
        </div>
      </details>
    `;
  },

  renderMessageBubble(msg) {
    const isUser = msg.role === 'user';
    const avatar = Atoms.renderAvatar(isUser ? 'user' : 'ai');
    const roleName = isUser ? 'Du' : 'Assistent';
    const bodyHtml = isUser ? Atoms.escapeHtml(msg.content).replace(/\n/g, '<br>') : this.parseMarkdown(msg.content);

    let metaHtml = '';
    if (!isUser) {
      metaHtml = this.renderMetaDetails(msg.model_used, msg.tool_calls, msg.token_usage);
    }

    return `
      <div class="message-row ${isUser ? 'user-row' : 'assistant-row'}" id="msg-${msg.id || Date.now()}">
        ${avatar}
        <div class="message-content-wrap">
          <div class="message-header">
            <span>${roleName}</span>
          </div>
          <div class="message-body">
            ${bodyHtml}
          </div>
          ${metaHtml ? `<div class="message-footer">${metaHtml}</div>` : ''}
        </div>
      </div>
    `;
  },

  renderSidebarItem(chat, isActive) {
    const activeClass = isActive ? 'active' : '';
    const safeTitle = Atoms.escapeHtml(chat.title || 'Neuer Chat');
    return `
      <div class="sidebar-chat-item ${activeClass}" onclick="Organisms.selectChat('${chat.id}')">
        ${Atoms.renderIcon('chat_bubble', 'chat-icon')}
        <span class="sidebar-chat-title" title="${safeTitle}">${safeTitle}</span>
        <div class="sidebar-chat-actions" onclick="event.stopPropagation()">
          <button class="btn-icon" title="Umbenennen" onclick="Organisms.promptRenameChat('${chat.id}', '${safeTitle.replace(/'/g, "\\'")}')">
            ${Atoms.renderIcon('edit', 'action-icon')}
          </button>
          <button class="btn-icon" title="Löschen" onclick="Organisms.confirmDeleteChat('${chat.id}')">
            ${Atoms.renderIcon('delete', 'action-icon')}
          </button>
        </div>
      </div>
    `;
  },

  renderPersonalityCard(persona, isSelected) {
    const selClass = isSelected ? 'selected' : '';
    return `
      <div class="personality-card ${selClass}" onclick="Organisms.selectPersonality('${persona.id}')">
        <div class="personality-card-header">
          ${Atoms.renderIcon(persona.icon || 'smart_toy')}
          <span>${Atoms.escapeHtml(persona.name)}</span>
        </div>
        <div class="personality-card-desc">
          ${Atoms.escapeHtml(persona.description)}
        </div>
      </div>
    `;
  },

  renderConnectionCard(conn, isDefault, index) {
    const defaultBadge = isDefault
      ? `<span class="badge" style="background: rgba(168, 199, 250, 0.16); color: var(--md-sys-color-primary); border: 1px solid var(--md-sys-color-primary);">${Atoms.renderIcon('check')} Standard</span>`
      : `<button class="btn btn-text" style="font-size: 11.5px; height: 28px; padding: 0 8px;" onclick="Organisms.setDefaultConnection('${conn.id}')">Als Standard</button>`;

    return `
      <div class="connection-card ${isDefault ? 'is-default' : ''}" id="conn-card-${index}">
        <div class="connection-card-header">
          <div class="connection-card-title">
            ${Atoms.renderIcon('hub', 'action-icon')}
            <input type="text" class="input-text" style="height: 34px; font-weight: 600; width: 220px;" value="${Atoms.escapeHtml(conn.name || 'Verbindung')}" placeholder="Name (z. B. Uni, Ollama)" onchange="Organisms.updateConnectionField(${index}, 'name', this.value)">
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            ${defaultBadge}
            <button class="btn-icon" title="Verbindung löschen" onclick="Organisms.deleteConnection(${index})">
              ${Atoms.renderIcon('delete')}
            </button>
          </div>
        </div>
        <div class="connection-card-grid">
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">Base URL (OpenAI-kompatibel)</label>
            <input type="text" class="input-text" style="height: 38px;" value="${Atoms.escapeHtml(conn.base_url || '')}" placeholder="http://localhost:11434/v1" onchange="Organisms.updateConnectionField(${index}, 'base_url', this.value)">
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">API Key / Token <span style="font-weight: normal; font-size: 11px; color: var(--md-sys-color-on-surface-variant);">(Optional)</span></label>
            <div style="position: relative; display: flex; align-items: center;">
              <input type="password" class="input-text" id="conn-card-key-${index}" style="height: 38px; padding-right: 36px;" value="${Atoms.escapeHtml(conn.api_key || '')}" placeholder="Optional (z. B. sk-...)" autocomplete="new-password" onchange="Organisms.updateConnectionField(${index}, 'api_key', this.value)">
              <button type="button" class="btn-icon" style="position: absolute; right: 4px; width: 28px; height: 28px;" onclick="Organisms.toggleCardKeyVisibility(${index})">
                <span class="material-symbols-outlined" id="conn-eye-${index}" style="font-size: 16px;">visibility</span>
              </button>
            </div>
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">Standard Modell-Name</label>
            <input type="text" class="input-text" style="height: 38px;" value="${Atoms.escapeHtml(conn.default_model || '')}" placeholder="z. B. google/gemma-4-31b-it oder llama3.2" onchange="Organisms.updateConnectionField(${index}, 'default_model', this.value)">
          </div>
          <div style="display: flex; flex-direction: column; justify-content: flex-end; gap: 6px;">
            <button class="btn btn-outlined" style="height: 38px; font-size: 12px; width: 100%;" onclick="Organisms.testSingleConnection(${index})">
              ${Atoms.renderIcon('network_check')} Verbindung testen
            </button>
            <div id="conn-test-result-${index}"></div>
          </div>
        </div>
      </div>
    `;
  },

  renderRuleCard(rule, index, connectionsList = []) {
    const isChecked = rule.active ? 'checked' : '';
    const keywordsVal = Array.isArray(rule.keywords)
      ? rule.keywords.join(', ')
      : (Array.isArray(rule.condition_value) ? rule.condition_value.join(', ') : (rule.keywords || rule.condition_value || ''));

    const connOptions = connectionsList.map(c => {
      const isSelected = (rule.target_connection === c.id) ? 'selected' : '';
      return `<option value="${c.id}" ${isSelected}>${Atoms.escapeHtml(c.name || c.id)}</option>`;
    }).join('');

    return `
      <div class="rule-card" id="rule-${index}">
        <div class="rule-card-header">
          <div class="rule-card-title">
            ${Atoms.renderIcon('alt_route')}
            <input type="text" class="input-text" style="height: 34px; font-weight: 600; width: 220px;" value="${Atoms.escapeHtml(rule.name)}" placeholder="Thema (z. B. Coding, Privat)" onchange="Organisms.updateRuleField(${index}, 'name', this.value)">
          </div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <label class="switch" title="Aktivieren / Deaktivieren">
              <input type="checkbox" ${isChecked} onchange="Organisms.updateRuleField(${index}, 'active', this.checked)">
              <span class="slider"></span>
            </label>
            <button class="btn-icon" title="Regel löschen" onclick="Organisms.deleteRule(${index})">
              ${Atoms.renderIcon('delete')}
            </button>
          </div>
        </div>
        <div class="rule-card-body">
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">Schlüsselwörter <span style="font-size: 11px; font-weight: normal; color: var(--md-sys-color-on-surface-variant);">(kommagetrennt)</span></label>
            <input type="text" class="input-text" style="height: 38px;" value="${Atoms.escapeHtml(String(keywordsVal))}" placeholder="z. B. python, code, sql, bug" onchange="Organisms.updateRuleKeywords(${index}, this.value)">
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">Ziel-Provider</label>
            <select class="select-box" style="height: 38px;" onchange="Organisms.updateRuleField(${index}, 'target_connection', this.value)">
              ${connOptions}
            </select>
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">Ziel-Modell</label>
            <input type="text" class="input-text" style="height: 38px;" value="${Atoms.escapeHtml(rule.target_model)}" placeholder="z. B. llama3.2 oder qwen3.8" onchange="Organisms.updateRuleField(${index}, 'target_model', this.value)">
          </div>
        </div>
      </div>
    `;
  }
};

window.Molecules = Molecules;
