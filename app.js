// Advisor Eval 2026 — static map + threaded comments viewer.

let ADVISORS = [];
let MARKERS_BY_INST = new Map();
let currentInstFilter = null;

const $ = (id) => document.getElementById(id);

async function main() {
  const res = await fetch('advisors.json');
  ADVISORS = await res.json();
  initMap();
  bindFilters();
  render();
}

let map, clusterLayer;

function initMap() {
  map = L.map('map', {
    worldCopyJump: true,
    center: [30, 0],
    zoom: 2,
    minZoom: 2,
    maxZoom: 13,
  });
  // Dark basemap via CARTO
  L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    { attribution: '&copy; OSM &copy; CARTO', subdomains: 'abcd', maxZoom: 19 }
  ).addTo(map);

  clusterLayer = L.markerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 40,
  });
  map.addLayer(clusterLayer);
}

function buildMarkers(filtered) {
  clusterLayer.clearLayers();
  MARKERS_BY_INST = new Map();
  // Group advisors by institution (to draw one marker per institution)
  const byInst = new Map();
  for (const a of filtered) {
    if (a.lat == null || a.lon == null) continue;
    const key = a.institution;
    if (!byInst.has(key))
      byInst.set(key, { institution: key, lat: a.lat, lon: a.lon, region: a.region, advisors: [] });
    byInst.get(key).advisors.push(a);
  }
  for (const entry of byInst.values()) {
    const count = entry.advisors.length;
    const blackCount = entry.advisors.filter(a => a.list_type === 'black' || a.list_type === 'both').length;
    const redCount = entry.advisors.filter(a => a.list_type === 'red' || a.list_type === 'both').length;
    const marker = L.circleMarker([entry.lat, entry.lon], {
      radius: Math.min(6 + Math.sqrt(count) * 2.2, 20),
      fillColor: blackCount > redCount ? '#ff6b6b' : (redCount > blackCount ? '#7cd189' : '#e8c773'),
      color: '#1c1f27',
      weight: 1.5,
      fillOpacity: 0.8,
    });
    const popup = `
      <div style="font-weight:600;margin-bottom:4px;">${escapeHtml(entry.institution)}</div>
      <div style="font-size:12px;color:#8c94a4;">${count} advisor${count === 1 ? '' : 's'} — ${blackCount} 黑 / ${redCount} 红</div>
      <a class="show-inst" data-inst="${escapeAttr(entry.institution)}">Show advisors →</a>`;
    marker.bindPopup(popup);
    marker.on('popupopen', (e) => {
      const el = e.popup.getElement();
      if (!el) return;
      const link = el.querySelector('.show-inst');
      if (link) link.onclick = () => {
        currentInstFilter = entry.institution;
        render();
        map.closePopup();
      };
    });
    clusterLayer.addLayer(marker);
    MARKERS_BY_INST.set(entry.institution, marker);
  }
}

function bindFilters() {
  for (const id of ['show-black', 'show-red', 'reveal-nsfw']) {
    $(id).addEventListener('change', render);
  }
  $('q').addEventListener('input', debounce(render, 150));
  $('clear-filter').addEventListener('click', () => {
    currentInstFilter = null;
    render();
  });
}

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

function filteredList() {
  const wantBlack = $('show-black').checked;
  const wantRed = $('show-red').checked;
  const q = $('q').value.trim().toLowerCase();
  return ADVISORS.filter(a => {
    if (a.list_type === 'black' && !wantBlack) return false;
    if (a.list_type === 'red' && !wantRed) return false;
    if (a.list_type === 'both' && !wantBlack && !wantRed) return false;
    if (currentInstFilter && a.institution !== currentInstFilter) return false;
    if (q) {
      const hay = (a.institution + ' ' + a.advisor + ' ' + (a.tag || '')).toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function render() {
  const list = filteredList();
  buildMarkers(list);
  renderList(list);
  $('count').textContent = `${list.length} entries`;
  $('clear-filter').hidden = !currentInstFilter;
  if (currentInstFilter) {
    $('clear-filter').textContent = `Clear filter: ${currentInstFilter}`;
  }
}

function renderList(list) {
  const container = $('advisor-list');
  if (list.length === 0) {
    container.innerHTML = '<div class="empty">No entries match your filters.</div>';
    return;
  }
  const revealNsfw = $('reveal-nsfw').checked;
  const parts = [];
  for (const a of list) {
    parts.push(renderCard(a, revealNsfw));
  }
  container.innerHTML = parts.join('');
  // Wire NSFW reveal buttons
  container.querySelectorAll('.nsfw-reveal').forEach(btn => {
    btn.addEventListener('click', () => {
      const box = btn.closest('.nsfw');
      const revealed = box.dataset.revealed === 'true';
      box.dataset.revealed = revealed ? 'false' : 'true';
      btn.textContent = revealed ? 'Reveal NSFW content' : 'Hide';
    });
  });
}

function renderCard(a, revealNsfw) {
  const listBadge =
    a.list_type === 'black' ? '<span class="badge black">🚩 Red Flag</span>' :
    a.list_type === 'red'   ? '<span class="badge red">★ Recommended</span>' :
                               '<span class="badge both">Both lists</span>';
  const region = a.region ? `<span class="badge region">${escapeHtml(a.region)}</span>` : '';
  const tag = a.tag ? `<span class="advisor-tag">${escapeHtml(a.tag)}</span>` : '';
  const cmts = (a.comments || []).map(c => renderComment(c, revealNsfw)).join('');
  return `
    <article class="advisor-card" id="adv-${slug(a.institution + '-' + a.advisor)}">
      <div class="advisor-head">
        <span class="advisor-name">${escapeHtml(a.advisor)}</span>
        <span class="advisor-inst">${escapeHtml(a.institution)}</span>
        ${region}
        ${listBadge}
        <span class="badge unverified">unverified</span>
        ${tag}
      </div>
      ${cmts ? `<ul class="comments">${cmts}</ul>` : '<div class="empty" style="padding:6px 0;">No comments.</div>'}
    </article>`;
}

function renderComment(c, revealNsfw) {
  const inner = `
    <div class="comment-text">${escapeHtml(c.text)}</div>
    ${c.replies && c.replies.length
      ? `<ul class="comment-replies comments">${c.replies.map(r => renderComment(r, revealNsfw)).join('')}</ul>`
      : ''}
  `;
  if (c.nsfw) {
    const revealed = revealNsfw ? 'true' : 'false';
    const btnTxt = revealNsfw ? 'Hide' : 'Reveal NSFW content';
    return `<li class="comment"><div class="nsfw" data-revealed="${revealed}"><button class="nsfw-reveal" type="button">${btnTxt}</button>${inner}</div></li>`;
  }
  return `<li class="comment">${inner}</li>`;
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}
function escapeAttr(s) { return escapeHtml(s); }
function slug(s) { return s.replace(/[^a-z0-9]+/gi, '-').toLowerCase(); }

main();
