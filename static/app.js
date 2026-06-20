/* ============================================
   BRIEFLEY 2.0 — Frontend (Legacy Theme)
   Unified feed, category filters, chat, settings
   ============================================ */

const API = '';

// ---- STATE ----
let allItems = [];       // Unified feed (clusters + standalone + telegram)
let activeFilter = 'all';
let activeStatFilter = 'all';

// ---- NAV ----
document.querySelectorAll('.nav-link').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-link').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById('page-' + btn.dataset.page).classList.add('active');
    });
});

// ---- HELPERS ----
function esc(t) { if (!t) return ''; const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
function initial(name) { return name ? name.replace('@','').charAt(0).toUpperCase() : '?'; }
function trunc(text, n=220) { return text && text.length > n ? text.substring(0,n) + '…' : (text||''); }

// Generic fallback — Briefly red B (last resort)
const FALLBACK_IMG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 200'%3E%3Crect width='400' height='200' fill='%231a1a1a'/%3E%3Ccircle cx='200' cy='100' r='50' fill='%23d42020'/%3E%3Ctext x='200' y='118' text-anchor='middle' fill='white' font-size='50' font-weight='900' font-family='sans-serif'%3EB%3C/text%3E%3C/svg%3E";

// Telegram logo as inline SVG (used for all Telegram channel fallbacks)
const TELEGRAM_IMG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 240'%3E%3Ccircle cx='120' cy='120' r='120' fill='%2329b6f6'/%3E%3Cpath fill='%23fff' d='M175 66L152 176c-2 7-6 9-12 5l-33-24-16 15c-2 2-4 3-7 3l2-34 57-51c3-2 0-3-3-1L76 130l-32-10c-7-2-7-7 2-10l121-47c6-2 11 2 8 10z'/%3E%3C/svg%3E";

// Source-specific fallback logos keyed by source_name (RSS feed names and Telegram usernames).
// Used when an article has no image_url, or when the image URL fails to load.
// Priority: source logo → FALLBACK_IMG generic B.
const SOURCE_LOGOS = {
    // ── International RSS ──────────────────────────────
    "BBC World":        "https://ichef.bbci.co.uk/news/1024/cpsprodpb/9A90/production/_97086593_defaultimage.png.webp",
    "Al Jazeera":       "https://www.aljazeera.com/favicon-32x32.png",
    "Daily News Egypt": "https://d1b3667xvzs6rz.cloudfront.net/2023/10/Dailynews-logo.png",
    "Coding Horror":    "https://blog.codinghorror.com/assets/images/codinghorror-app-icon.png?v=c8e4b9197a",
    // ── Egypt RSS ──────────────────────────────────────
    "Youm7":            "https://img.youm7.com/images/graphics/logoyoum7.png",
    "Al Bawaba":        "https://www.albawabhnews.com/themes/bawaba/assets/images/logo.png",
    "Masrawy":          "https://th.bing.com/th/id/OIP.vKF9uBSgjCZYXM-n28mBEAHaEK?rs=1&pid=ImgDetMain",
    "Egyptian Streets": "https://egyptianstreets.com/wp-content/uploads/2022/07/egysinai.jpg",
    // ── Telegram channels (usernames, no @) ───────────
    "aljazeera":        TELEGRAM_IMG,
    "SkyNewsArabia_B":  TELEGRAM_IMG,
    "rtarabictelegram": TELEGRAM_IMG,
    "AlJazeeraEnglish": TELEGRAM_IMG,
    "hanzpal20":        TELEGRAM_IMG,
    "Middle_East_Spectator": TELEGRAM_IMG,
    "thecradlemedia":   TELEGRAM_IMG,
    "Faytuks":          TELEGRAM_IMG,
    "ME_Observer_":     TELEGRAM_IMG,
    "disclosetv":       TELEGRAM_IMG,
    "BNO_News":         TELEGRAM_IMG,
    "atlasnewstelegram":TELEGRAM_IMG,
    "IntelPointAlert":  TELEGRAM_IMG,
    "war_monitor":      TELEGRAM_IMG,
    "DDGeopolitics":    TELEGRAM_IMG,
    "DefenseArab":      TELEGRAM_IMG,
    "geopolitics_live": TELEGRAM_IMG,
    "AUKUS_news":       TELEGRAM_IMG,
    "SouthFrontEng":    TELEGRAM_IMG,
};

/** Return the source-specific logo, or the generic fallback if none is registered. */
function getSourceFallback(sourceName) {
    return SOURCE_LOGOS[sourceName] || FALLBACK_IMG;
}

// ---- LOAD FEED ----
async function loadFeed() {
    try {
        const res = await fetch(API + '/api/feed');
        const data = await res.json();
        const feedItems = data.feed || [];
        const tgItems = data.telegram || [];

        // Build unified list
        allItems = [];

        feedItems.forEach((item, idx) => {
            if (item.type === 'cluster') {
                const m = item.main;
                const isTg = (m.source_name||'').startsWith('@') || isTelegramSource(m.source_name);
                allItems.push({
                    _type: 'cluster',
                    _idx: idx,
                    category: m.category || 'General',
                    title: m.title || 'Breaking Event',
                    summary: m.summary_text || m.full_text || '',
                    image: m.image_url,
                    source: m.source_name || m.channel || 'Unknown',
                    time: m.formatted_time || '',
                    dt: m._dt || '',
                    count: item.count || item.articles.length,
                    articles: item.articles,
                    cluster_id: item.cluster_id,
                    isTelegram: isTg,
                });
            } else {
                const a = item.article;
                const isTg = (a.source_name||'').startsWith('@') || isTelegramSource(a.source_name);
                allItems.push({
                    _type: 'standalone',
                    category: a.category || 'General',
                    title: a.title || 'Untitled',
                    summary: a.summary_text || a.full_text || '',
                    image: a.image_url,
                    source: a.source_name || a.channel || 'Unknown',
                    time: a.formatted_time || '',
                    dt: a._dt || '',
                    url: a.url,
                    isTelegram: isTg,
                    cluster_id: a.cluster_id,
                });
            }
        });

        updateStats(feedItems, tgItems);
        buildFilterBar();
        renderFeed();
        document.getElementById('status-text').textContent = 'Live';
    } catch(e) {
        document.getElementById('status-text').textContent = 'Offline';
        document.getElementById('feed-container').innerHTML =
            '<div class="empty-state"><div class="icon">⚡</div><p>Cannot reach the backend. Ensure the server and Qdrant are running.</p></div>';
    }
}

// Simple check for known telegram channel names
function isTelegramSource(name) {
    if (!name) return false;
    // Telegram sources won't have spaces typically, or start with @
    const knownTg = ['aljazeera','SkyNewsArabia_B','rtarabictelegram','hanzpal20',
        'Middle_East_Spectator','thecradlemedia','Faytuks','ME_Observer_',
        'AlJazeeraEnglish','disclosetv','BNO_News','atlasnewstelegram',
        'IntelPointAlert','war_monitor','DDGeopolitics','DefenseArab',
        'geopolitics_live','AUKUS_news','SouthFrontEng'];
    return knownTg.includes(name);
}

function updateStats(feedItems, tgItems) {
    let total = 0, clusters = 0;
    const sources = new Set();
    feedItems.forEach(i => {
        if (i.type === 'cluster') {
            clusters++;
            total += i.articles.length;
            i.articles.forEach(a => sources.add(a.source_name || a.channel || ''));
        } else {
            total++;
            sources.add(i.article.source_name || i.article.channel || '');
        }
    });
    document.getElementById('s-total').textContent = total;
    document.getElementById('s-clusters').textContent = clusters;
    document.getElementById('s-sources').textContent = sources.size;
    document.getElementById('s-tg').textContent = tgItems.length;
}

function filterFeedByStat(statName) {
    if (statName === 'sources') {
        // "Sources" click opens the drawer to manage them
        openDrawer();
        return;
    }
    
    if (activeStatFilter === statName) {
        activeStatFilter = 'all'; // Toggle off if clicked again
    } else {
        activeStatFilter = statName;
    }
    
    // Update UI active states
    document.querySelectorAll('.stat').forEach(el => el.classList.remove('active'));
    if (activeStatFilter !== 'all') {
        const el = document.getElementById('stat-' + activeStatFilter);
        if (el) el.classList.add('active');
    }
    
    renderFeed();
}

// ---- FILTER BAR ----
function buildFilterBar() {
    const cats = new Set(['all']);
    allItems.forEach(i => { if (i.category) cats.add(i.category); });

    const bar = document.getElementById('filter-bar');
    bar.innerHTML = '';
    cats.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = 'filter-pill' + (cat === activeFilter ? ' active' : '');
        btn.textContent = cat === 'all' ? 'All' : cat;
        btn.onclick = () => { activeFilter = cat; buildFilterBar(); renderFeed(); };
        bar.appendChild(btn);
    });
}

// ---- RENDER ----
function renderFeed() {
    const container = document.getElementById('feed-container');
    let items = allItems;
    
    // 1. Category Filter
    if (activeFilter !== 'all') {
        items = items.filter(i => i.category === activeFilter);
    }
    
    // 2. Stat Filter
    if (activeStatFilter === 'articles') {
        items = items.filter(i => !i.isTelegram && i._type !== 'cluster');
    } else if (activeStatFilter === 'clusters') {
        items = items.filter(i => i._type === 'cluster');
    } else if (activeStatFilter === 'telegram') {
        items = items.filter(i => i.isTelegram);
    }

    if (!items.length) {
        container.innerHTML = '<div class="empty-state"><div class="icon">📭</div><p>No articles found. Run <code>python async_ingest.py</code></p></div>';
        return;
    }

    container.innerHTML = items.map((item, idx) => {
        // Use the source-specific logo when no image_url is available
        const imgSrc = (item.image && item.image.match(/^http/)) ? esc(item.image) : getSourceFallback(item.source);
        const sourceBadge = item.isTelegram
            ? '<span class="pill pill-telegram">📡 Telegram</span>'
            : '';

        // Trust label for telegram items
        let trustBadge = '';
        if (item.isTelegram) {
            const cid = String(item.cluster_id || '-1');
            if (cid !== '-1') trustBadge = '<span class="pill pill-corroborated">✓ Verified</span>';
            else if ((item.summary||'').length > 100) trustBadge = '<span class="pill pill-novel">⚠ Novel</span>';
            else trustBadge = '<span class="pill pill-orphan">✗ Unverified</span>';
        }

        if (item._type === 'cluster') {
            const sourcesHtml = item.articles.map(a => {
                const s = a.source_name || a.channel || '?';
                return `<div class="cluster-source-row"><div class="source-dot">${initial(s)}</div><strong>${esc(s)}</strong>: <a href="${esc(a.url||'#')}" target="_blank">${esc(a.title||'Untitled')}</a></div>`;
            }).join('');

            return `<div class="card">
                <img class="card-img" src="${imgSrc}" alt="" data-source="${esc(item.source)}" onerror="this.onerror=null;this.src=getSourceFallback(this.dataset.source)">
                <div class="card-body">
                    <div class="card-badges">
                        <span class="pill pill-category">${esc(item.category)}</span>
                        <span class="pill pill-cluster">🔗 ${item.count} stories</span>
                        ${sourceBadge}${trustBadge}
                    </div>
                    <div class="card-title">${esc(item.title)}</div>
                    <div class="card-summary">${esc(trunc(item.summary))}</div>
                    <div class="card-footer">
                        <div class="card-source-info"><div class="source-dot">${initial(item.source)}</div><span>${esc(item.source)}</span></div>
                        <span>${esc(item.time)}</span>
                    </div>
                </div>
                <div class="cluster-details" id="cl-${idx}">${sourcesHtml}</div>
                <button class="expand-btn" onclick="event.stopPropagation();document.getElementById('cl-${idx}').classList.toggle('open')">View sources ▾</button>
            </div>`;
        } else {
            return `<div class="card" ${item.url ? `onclick="window.open('${esc(item.url)}','_blank')"` : ''}>
                <img class="card-img" src="${imgSrc}" alt="" data-source="${esc(item.source)}" onerror="this.onerror=null;this.src=getSourceFallback(this.dataset.source)">
                <div class="card-body">
                    <div class="card-badges">
                        <span class="pill pill-category">${esc(item.category)}</span>
                        ${sourceBadge}${trustBadge}
                    </div>
                    <div class="card-title">${esc(item.title)}</div>
                    <div class="card-summary">${esc(trunc(item.summary))}</div>
                    <div class="card-footer">
                        <div class="card-source-info"><div class="source-dot">${initial(item.source)}</div><span>${esc(item.source)}</span></div>
                        <span>${esc(item.time)}</span>
                    </div>
                </div>
            </div>`;
        }
    }).join('');
}

// ---- CHAT ----
const chatMsgs = document.getElementById('chat-messages');
const chatIn = document.getElementById('chat-input');
const chatBtn = document.getElementById('chat-send');

function addMsg(role, text) {
    const isUser = role === 'user';
    const div = document.createElement('div');
    div.className = 'chat-msg ' + (isUser ? 'user' : 'bot');
    div.innerHTML = `<div class="chat-avatar">${isUser ? 'U' : 'B'}</div><div class="chat-bubble">${esc(text)}</div>`;
    chatMsgs.appendChild(div);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;
}

async function sendChat() {
    const text = chatIn.value.trim();
    if (!text) return;
    addMsg('user', text);
    chatIn.value = '';
    chatBtn.disabled = true;

    const tid = 'th-' + Date.now();
    const th = document.createElement('div');
    th.className = 'chat-msg bot'; th.id = tid;
    th.innerHTML = '<div class="chat-avatar">B</div><div class="chat-bubble"><div class="spinner" style="display:inline-block;width:14px;height:14px;border-width:2px;margin-right:6px;vertical-align:middle"></div>Searching…</div>';
    chatMsgs.appendChild(th);
    chatMsgs.scrollTop = chatMsgs.scrollHeight;

    try {
        const res = await fetch(API + '/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: text})
        });
        const data = await res.json();
        th.remove();
        addMsg('bot', data.response || 'No response.');
    } catch(e) {
        th.remove();
        addMsg('bot', '⚠️ Could not reach RAG engine. Is Ollama running?');
    }
    chatBtn.disabled = false;
    chatIn.focus();
}

chatBtn.addEventListener('click', sendChat);
chatIn.addEventListener('keydown', e => { if (e.key === 'Enter') sendChat(); });

// ---- SETTINGS ----
async function loadSettings() {
    try {
        const res = await fetch(API + '/api/settings');
        const s = await res.json();
        window.brieflySettings = s;
        renderSettings(s);
    } catch(e) {
        document.getElementById('settings-container').innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><p>Could not load settings.</p></div>';
    }
}

function renderSettings(s) {
    const c = document.getElementById('settings-container');
    const aRss = s.active_rss || [];
    const aCh = s.active_channels || [];
    let html = '';

    for (const [cat, feeds] of Object.entries(s.available_rss || {})) {
        html += `<div class="settings-section"><h3>📰 ${esc(cat)}</h3>`;
        feeds.forEach(f => {
            html += `<div class="settings-item"><span class="settings-item-name">${esc(f)}</span>
                <label class="toggle"><input type="checkbox" ${aRss.includes(f)?'checked':''} onchange="toggleSrc('rss','${esc(f)}',this.checked)"><span class="slider"></span></label></div>`;
        });
        html += '</div>';
    }

    for (const [cat, chs] of Object.entries(s.available_channels || {})) {
        html += `<div class="settings-section"><h3>📡 ${esc(cat)}</h3>`;
        chs.forEach(ch => {
            html += `<div class="settings-item"><span class="settings-item-name">@${esc(ch)}</span>
                <label class="toggle"><input type="checkbox" ${aCh.includes(ch)?'checked':''} onchange="toggleSrc('channel','${esc(ch)}',this.checked)"><span class="slider"></span></label></div>`;
        });
        html += '</div>';
    }

    c.innerHTML = html;
}

async function toggleSrc(type, name, on) {
    const ep = type === 'rss' ? '/api/rss/toggle' : '/api/channels/toggle';
    try { await fetch(API + ep, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name, action: on?'add':'remove'}) }); } catch(e) {}
}

// ---- INIT ----
loadFeed();
loadSettings();

// ---- ADD RESOURCE DRAWER ----
function openDrawer() {
    document.getElementById('drawer-overlay').classList.add('show');
    document.getElementById('add-drawer').classList.add('open');
    switchDrawerTab('rss'); // default
    
    // Populate Categories
    const select = document.getElementById('res-category-select');
    const customOption = select.querySelector('option[value="other"]');
    select.innerHTML = '';
    
    const categories = new Set();
    if (window.brieflySettings) {
        Object.keys(window.brieflySettings.available_rss || {}).forEach(c => categories.add(c));
        Object.keys(window.brieflySettings.available_channels || {}).forEach(c => categories.add(c));
    }
    categories.add("World News");
    categories.add("Middle East & Egypt");
    categories.add("Technology");
    // Remove "Other" from default set if present, we'll append it at the end
    categories.delete("Other");
    
    Array.from(categories).sort().forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat;
        opt.textContent = cat;
        select.appendChild(opt);
    });
    if (customOption) select.appendChild(customOption);
    else select.insertAdjacentHTML('beforeend', '<option value="other">Other...</option>');
    
    select.value = Array.from(categories)[0] || "World News";
    toggleCustomCategory();
}

function closeDrawer() {
    document.getElementById('drawer-overlay').classList.remove('show');
    document.getElementById('add-drawer').classList.remove('open');
    document.getElementById('res-name').value = '';
    document.getElementById('res-url').value = '';
    document.getElementById('res-category').value = '';
}

function toggleCustomCategory() {
    const select = document.getElementById('res-category-select');
    const input = document.getElementById('res-category');
    if (select.value === 'other') {
        input.style.display = 'block';
    } else {
        input.style.display = 'none';
        input.value = '';
    }
}

function switchDrawerTab(type) {
    document.getElementById('res-type').value = type;
    
    // Update active tab UI
    document.querySelectorAll('.drawer-nav-item').forEach(btn => btn.classList.remove('active'));
    event.currentTarget.classList.add('active');

    const urlGroup = document.getElementById('res-url-group');
    const nameLabel = document.getElementById('res-name-label');
    
    if (type === 'rss') {
        urlGroup.style.display = 'block';
        nameLabel.textContent = "Feed Name";
    } else if (type === 'telegram') {
        urlGroup.style.display = 'none';
        nameLabel.textContent = "Telegram @username";
    } else if (type === 'telegram_list') {
        urlGroup.style.display = 'none';
        nameLabel.textContent = "Comma-separated @usernames";
    }
}

async function submitNewResource() {
    const type = document.getElementById('res-type').value;
    let name = document.getElementById('res-name').value.trim();
    const url = document.getElementById('res-url').value.trim();
    
    const sel = document.getElementById('res-category-select').value;
    let category = sel === 'other' ? document.getElementById('res-category').value.trim() : sel;
    
    if (!name) { alert("Name/Username is required"); return; }
    if (type === 'rss' && !url) { alert("URL is required"); return; }
    if (!category) { alert("Category is required"); return; }

    const payload = { type, name, url, category };
    const btn = document.querySelector('.submit-res-btn');
    btn.textContent = 'Adding...'; btn.disabled = true;

    try {
        const res = await fetch(API + '/api/resources/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeDrawer();
            loadSettings(); // refresh list
        } else {
            alert("Error adding resource");
        }
    } catch(e) {
        alert("Network error.");
    }
    btn.textContent = 'Add Source'; btn.disabled = false;
}

