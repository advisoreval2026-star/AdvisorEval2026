// Advisor Eval 2026 — static frontend that reads live data from Supabase.

let ADVISORS = [];                // [{ key, name, university, region, lat, lon, list_type, tag }]
let COMMENTS_BY_ADVISOR = null;   // lazy-built: key -> threaded comment tree
let ALL_COMMENT_ROWS = [];        // raw rows from Supabase (cached after first fetch)
let MARKERS_BY_INST = new Map();
let currentInstFilter = null;
let sb = null;

const $ = (id) => document.getElementById(id);

async function main() {
  if (!window.supabase || !window.SUPABASE_URL) {
    $('advisor-list').innerHTML =
      '<div class="empty">Supabase not configured (check config.js).</div>';
    return;
  }
  sb = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY, {
    auth: { persistSession: false },
  });
  initMap();
  bindFilters();
  await loadAdvisors();
  render();
  // Fetch comments in the background; re-render when ready.
  loadAllComments().then(render);
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
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png', {
    attribution: '&copy; OSM &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map);
  clusterLayer = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 40 });
  map.addLayer(clusterLayer);
}

async function loadAdvisors() {
  const { data, error } = await sb
    .from('advisors')
    .select('key,name,university,region,lat,lon,list_type,tag')
    .order('university', { ascending: true });
  if (error) {
    console.error('loadAdvisors', error);
    ADVISORS = [];
    return;
  }
  ADVISORS = data || [];
}

async function loadAllComments() {
  // Single round-trip: pull all comments, build threads per-advisor on the client.
  // Supabase default row limit is 1000 — raise via range header if needed.
  const PAGE = 1000;
  let offset = 0;
  const all = [];
  while (true) {
    const { data, error } = await sb
      .from('comments')
      .select('id,advisor_key,parent_id,body,source,nsfw,score,created_at')
      .order('created_at', { ascending: true })
      .range(offset, offset + PAGE - 1);
    if (error) { console.error('loadComments', error); break; }
    if (!data || data.length === 0) break;
    all.push(...data);
    if (data.length < PAGE) break;
    offset += PAGE;
  }
  ALL_COMMENT_ROWS = all;
  COMMENTS_BY_ADVISOR = buildThreadsByAdvisor(all);
}

function buildThreadsByAdvisor(rows) {
  const byId = new Map();
  const byAdvisor = new Map();
  for (const r of rows) {
    r.replies = [];
    byId.set(r.id, r);
  }
  for (const r of rows) {
    if (r.parent_id && byId.has(r.parent_id)) {
      byId.get(r.parent_id).replies.push(r);
    } else {
      if (!byAdvisor.has(r.advisor_key)) byAdvisor.set(r.advisor_key, []);
      byAdvisor.get(r.advisor_key).push(r);
    }
  }
  return byAdvisor;
}

function buildMarkers(filtered) {
  clusterLayer.clearLayers();
  MARKERS_BY_INST = new Map();
  const byInst = new Map();
  for (const a of filtered) {
    if (a.lat == null || a.lon == null) continue;
    const key = a.university;
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
  $('clear-filter').addEventListener('click', () => { currentInstFilter = null; render(); });
}

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function filteredList() {
  const wantBlack = $('show-black').checked;
  const wantRed = $('show-red').checked;
  const q = $('q').value.trim().toLowerCase();
  return ADVISORS.filter(a => {
    if (a.list_type === 'black' && !wantBlack) return false;
    if (a.list_type === 'red' && !wantRed) return false;
    if (a.list_type === 'both' && !wantBlack && !wantRed) return false;
    if (currentInstFilter && a.university !== currentInstFilter) return false;
    if (q) {
      const hay = (a.university + ' ' + a.name + ' ' + (a.tag || '')).toLowerCase();
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
  if (currentInstFilter) $('clear-filter').textContent = `Clear filter: ${currentInstFilter}`;
}

function renderList(list) {
  const container = $('advisor-list');
  if (list.length === 0) {
    container.innerHTML = '<div class="empty">No entries match your filters.</div>';
    return;
  }
  const revealNsfw = $('reveal-nsfw').checked;
  const parts = [];
  for (const a of list) parts.push(renderCard(a, revealNsfw));
  container.innerHTML = parts.join('');
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
  const advisorKey = `${a.name}|${a.university}`;
  const threads = COMMENTS_BY_ADVISOR ? (COMMENTS_BY_ADVISOR.get(advisorKey) || []) : null;
  let body;
  if (threads === null) {
    body = '<div class="empty" style="padding:6px 0;">Loading comments…</div>';
  } else if (threads.length === 0) {
    body = '<div class="empty" style="padding:6px 0;">No comments.</div>';
  } else {
    body = `<ul class="comments">${threads.map(c => renderComment(c, revealNsfw)).join('')}</ul>`;
  }
  return `
    <article class="advisor-card" id="adv-${slug(a.university + '-' + a.name)}">
      <div class="advisor-head">
        <span class="advisor-name">${escapeHtml(a.name)}</span>
        <span class="advisor-inst">${escapeHtml(a.university)}</span>
        ${region}
        ${listBadge}
        <span class="badge unverified">unverified</span>
        ${tag}
      </div>
      ${body}
    </article>`;
}

function renderComment(c, revealNsfw) {
  const inner = `
    <div class="comment-text">${escapeHtml(c.body)}</div>
    ${c.replies && c.replies.length
      ? `<ul class="comment-replies comments">${c.replies.map(r => renderComment(r, revealNsfw)).join('')}</ul>`
      : ''}
  `;
  const sourceBadge = c.source === 'user' ? ' <span class="badge region" style="margin-left:4px;">user</span>' : '';
  if (c.nsfw) {
    const revealed = revealNsfw ? 'true' : 'false';
    const btnTxt = revealNsfw ? 'Hide' : 'Reveal NSFW content';
    return `<li class="comment"><div class="nsfw" data-revealed="${revealed}"><button class="nsfw-reveal" type="button">${btnTxt}</button>${sourceBadge}${inner}</div></li>`;
  }
  return `<li class="comment">${sourceBadge}${inner}</li>`;
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}
function escapeAttr(s) { return escapeHtml(s); }
function slug(s) { return s.replace(/[^a-z0-9]+/gi, '-').toLowerCase(); }

main();
