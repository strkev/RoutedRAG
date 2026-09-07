// ==========================================================================
// ATOMIC DESIGN LEVEL 2: MOLECULE RENDERERS
// ==========================================================================

const Molecules = {
  parseMarkdown(text) {
    if (!text) return '';
    let html = Atoms.escapeHtml(text);

    // Code blocks with syntax highlighting container
    html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      const language = lang || 'code';
      return `
        <div class="code-block-container" style="position: relative; margin: 12px 0;">
          <div style="display: flex; justify-content: space-between; align-items: center; background: #202224; padding: 4px 12px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-size: 11px; color: #8e918f; border: 1px solid var(--md-sys-color-outline-variant); border-bottom: none;">
            <span>${language}</span>
            <button class="btn btn-text" style="height: 24px; padding: 0 6px; font-size: 11px;" onclick="Molecules.copyCode(this)">Kopieren</button>
          </div>
          <pre style="margin: 0; border-top-left-radius: 0; border-top-right-radius: 0;"><code>${code}</code></pre>
        </div>
      `;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold & Italics
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3 style="font-size: 16px; margin: 12px 0 6px 0; color: var(--md-sys-color-primary);">$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2 style="font-size: 18px; margin: 14px 0 8px 0; color: var(--md-sys-color-on-surface);">$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1 style="font-size: 20px; margin: 16px 0 10px 0; color: var(--md-sys-color-on-surface);">$1</h1>');

    // Unordered lists
    html = html.replace(/^\s*-\s+(.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Paragraph breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    return `<p>${html}</p>`;
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

  renderRuleCard(rule, index) {
    const isChecked = rule.active ? 'checked' : '';
    const condVal = Array.isArray(rule.condition_value) ? rule.condition_value.join(', ') : rule.condition_value;
    
    return `
      <div class="rule-card" id="rule-${index}">
        <div class="rule-card-header">
          <div class="rule-card-title">
            ${Atoms.renderIcon('rule')}
            <input type="text" class="input-text" style="height: 34px; font-weight: 600; width: 220px;" value="${Atoms.escapeHtml(rule.name)}" onchange="Organisms.updateRuleField(${index}, 'name', this.value)">
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
            <label class="form-label">Bedingungstyp</label>
            <select class="select-box" style="height: 38px;" onchange="Organisms.updateRuleField(${index}, 'condition_type', this.value)">
              <option value="contains_any" ${rule.condition_type === 'contains_any' ? 'selected' : ''}>contains_any (Schlüsselwörter)</option>
              <option value="role_equals" ${rule.condition_type === 'role_equals' ? 'selected' : ''}>role_equals (Benutzerrolle)</option>
              <option value="min_length" ${rule.condition_type === 'min_length' ? 'selected' : ''}>min_length (Minimale Länge)</option>
            </select>
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">Bedingungswert</label>
            <input type="text" class="input-text" style="height: 38px;" value="${Atoms.escapeHtml(String(condVal))}" placeholder="z. B. def, class, sql" onchange="Organisms.updateRuleValue(${index}, this.value)">
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">Ziel-Modell</label>
            <input type="text" class="input-text" style="height: 38px;" value="${Atoms.escapeHtml(rule.target_model)}" placeholder="z. B. qwen/qwen3.8-27B-fp8" onchange="Organisms.updateRuleField(${index}, 'target_model', this.value)">
          </div>
        </div>
      </div>
    `;
  }
};

window.Molecules = Molecules;
