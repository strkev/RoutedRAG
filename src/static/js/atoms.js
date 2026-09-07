// ==========================================================================
// ATOMIC DESIGN LEVEL 1: ATOM RENDERERS
// ==========================================================================

const Atoms = {
  escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  },

  renderIcon(iconName, className = '') {
    return `<span class="material-symbols-outlined ${className}">${iconName}</span>`;
  },

  renderBadge(text, type = 'primary', icon = null) {
    const iconHtml = icon ? this.renderIcon(icon) : '';
    return `<span class="badge badge-${type}">${iconHtml} ${this.escapeHtml(text)}</span>`;
  },

  renderToggleSwitch(id, checked = false, onChangeFnName = '') {
    const isChecked = checked ? 'checked' : '';
    const onchangeAttr = onChangeFnName ? `onchange="${onChangeFnName}(this.checked)"` : '';
    return `
      <label class="switch" for="${id}">
        <input type="checkbox" id="${id}" ${isChecked} ${onchangeAttr}>
        <span class="slider"></span>
      </label>
    `;
  },

  renderButton({ text, icon = null, variant = 'filled', className = '', onClick = '', title = '' }) {
    const iconHtml = icon ? this.renderIcon(icon) : '';
    const clickAttr = onClick ? `onclick="${onClick}"` : '';
    const titleAttr = title ? `title="${this.escapeHtml(title)}"` : '';
    return `
      <button class="btn btn-${variant} ${className}" ${clickAttr} ${titleAttr}>
        ${iconHtml}
        ${text ? `<span>${this.escapeHtml(text)}</span>` : ''}
      </button>
    `;
  },

  renderAvatar(type = 'ai', initial = '') {
    if (type === 'ai') {
      return `<div class="avatar avatar-ai">${this.renderIcon('smart_toy')}</div>`;
    }
    return `<div class="avatar avatar-user">${this.renderIcon('person')}</div>`;
  }
};

window.Atoms = Atoms;
