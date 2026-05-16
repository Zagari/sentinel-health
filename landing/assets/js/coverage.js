/* =============================================================================
   Sentinel Health — Coverage page logic
   Fetches coverage-data.json (canonical source) and renders the matrix
   with multi-axis filters.
   ============================================================================= */

const STATUS_META = {
  ok:      { label: 'Atendido', icon: '✅', cssClass: 'status-ok' },
  partial: { label: 'Parcial',  icon: '⚠️', cssClass: 'status-partial' },
  roadmap: { label: 'Roadmap',  icon: '🚀', cssClass: 'status-roadmap' },
};

const MODULE_META = {
  surgical: { label: 'Surgical', url: '/surgical/' },
  insight:  { label: 'Insight',  url: '/insight/' },
};

const SECTION_META = {
  functionality: 'Funcionalidades',
  objective:     'Objetivos',
  video:         'Req. 1 — Vídeo',
  audio:         'Req. 2 — Áudio',
  deliverables:  'Entregáveis',
};

let allItems = [];
const filters = { status: 'all', data_type: 'all', section: 'all' };

// ── Escape utility ──────────────────────────────────────────────────────────
function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

// ── Initial load ────────────────────────────────────────────────────────────
async function init() {
  try {
    const res = await fetch('/assets/coverage-data.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Flatten items, tagging each with its section key
    allItems = [];
    for (const [sectionKey, sectionData] of Object.entries(data.categories)) {
      for (const item of sectionData.items) {
        allItems.push({ ...item, section: sectionKey });
      }
    }

    updateStats();
    bindFilters();
    render();
  } catch (err) {
    document.getElementById('results-count').textContent =
      `Erro ao carregar matriz: ${err.message}`;
    console.error('Failed to load coverage-data.json:', err);
  }
}

// ── Global stats (top of page) ──────────────────────────────────────────────
function updateStats() {
  const counts = { ok: 0, partial: 0, roadmap: 0 };
  for (const item of allItems) counts[item.status]++;

  document.querySelector('[data-stat="ok"]').textContent       = counts.ok;
  document.querySelector('[data-stat="partial"]').textContent  = counts.partial;
  document.querySelector('[data-stat="roadmap"]').textContent  = counts.roadmap;
  document.querySelector('[data-stat="total"]').textContent    = allItems.length;
}

// ── Bind chip clicks ────────────────────────────────────────────────────────
function bindFilters() {
  document.querySelectorAll('.chips').forEach(group => {
    const filterName = group.dataset.filter;
    group.querySelectorAll('.chip').forEach(chip => {
      chip.addEventListener('click', () => {
        group.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        filters[filterName] = chip.dataset.value;
        render();
      });
    });
  });

  document.getElementById('reset-filters').addEventListener('click', () => {
    filters.status = 'all';
    filters.data_type = 'all';
    filters.section = 'all';
    document.querySelectorAll('.chips').forEach(group => {
      group.querySelectorAll('.chip').forEach(c => {
        c.classList.toggle('active', c.dataset.value === 'all');
      });
    });
    render();
  });
}

// ── Filter logic ────────────────────────────────────────────────────────────
function matchesFilters(item) {
  if (filters.status !== 'all'    && item.status    !== filters.status)    return false;
  if (filters.data_type !== 'all' && item.data_type !== filters.data_type) return false;
  if (filters.section !== 'all'   && item.section   !== filters.section)   return false;
  return true;
}

// ── Render items ────────────────────────────────────────────────────────────
function render() {
  const list = document.getElementById('items-list');
  const empty = document.getElementById('empty-state');
  const counter = document.getElementById('results-count');

  const visible = allItems.filter(matchesFilters);

  // Counter line with per-status breakdown for the current filter set
  const visibleCounts = { ok: 0, partial: 0, roadmap: 0 };
  visible.forEach(i => visibleCounts[i.status]++);
  counter.innerHTML = visible.length === allItems.length
    ? `Mostrando <strong>${allItems.length}</strong> itens (` +
      `${visibleCounts.ok} ✅ · ${visibleCounts.partial} ⚠️ · ${visibleCounts.roadmap} 🚀)`
    : `Mostrando <strong>${visible.length}</strong> de ${allItems.length} itens (` +
      `${visibleCounts.ok} ✅ · ${visibleCounts.partial} ⚠️ · ${visibleCounts.roadmap} 🚀)`;

  list.innerHTML = '';
  if (visible.length === 0) {
    empty.hidden = false;
    return;
  }
  empty.hidden = true;

  for (const item of visible) {
    list.appendChild(renderItem(item));
  }
}

// ── Render a single item card ───────────────────────────────────────────────
function renderItem(item) {
  const card = document.createElement('article');
  const meta = STATUS_META[item.status] || STATUS_META.partial;
  card.className = `item-card ${meta.cssClass}`;
  card.dataset.itemId = item.id;

  // Module badges (clickable when there's a module_url)
  let modulesHtml = '';
  if (Array.isArray(item.modules) && item.modules.length > 0) {
    const badges = item.modules.map(m => {
      const mmeta = MODULE_META[m] || { label: m, url: null };
      if (mmeta.url) {
        return `<a class="module-badge module-badge-${escapeHtml(m)}" href="${escapeHtml(mmeta.url)}">${escapeHtml(mmeta.label)}</a>`;
      }
      return `<span class="module-badge module-badge-${escapeHtml(m)}">${escapeHtml(mmeta.label)}</span>`;
    }).join('');
    modulesHtml = `<div class="item-modules">${badges}</div>`;
  } else {
    modulesHtml = `<div class="item-modules item-modules-empty"><span class="module-badge module-badge-none">— sem módulo associado —</span></div>`;
  }

  card.innerHTML = `
    <div class="item-head">
      <span class="status-badge ${meta.cssClass}">${meta.icon} ${escapeHtml(meta.label)}</span>
      <span class="section-badge">${escapeHtml(SECTION_META[item.section] || item.section)}</span>
      <span class="item-id" title="Identificador do item">${escapeHtml(item.id)}</span>
    </div>
    <h3 class="item-req">${escapeHtml(item.requirement)}</h3>
    <p class="item-evidence">${escapeHtml(item.evidence)}</p>
    ${modulesHtml}
  `;
  return card;
}

// ── Boot ────────────────────────────────────────────────────────────────────
init();
