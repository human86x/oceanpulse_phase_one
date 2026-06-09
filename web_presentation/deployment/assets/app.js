// SPEC-032 Internal Roadmap Panel — client
(() => {
'use strict';

const API = 'api.php';
const LANG_KEY = 'op_deploy_lang';
let state = null;
let lang = localStorage.getItem(LANG_KEY) || 'en';

// ---------- Utilities ----------
const $  = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));

function timeAgo(iso) {
    if (!iso) return '';
    const then = new Date(iso).getTime();
    if (isNaN(then)) return '';
    const s = Math.max(0, Math.floor((Date.now() - then) / 1000));
    if (s < 60)    return s + 's ago';
    if (s < 3600)  return Math.floor(s/60) + 'm ago';
    if (s < 86400) return Math.floor(s/3600) + 'h ago';
    return Math.floor(s/86400) + 'd ago';
}

function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => (
        {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]
    ));
}

function t(key) {
    const u = state?.ui_strings?.[key];
    if (u) return u[lang] ?? u.en ?? key;
    return key;
}

function toast(msg, isError=false) {
    const el = $('#toast');
    el.textContent = msg;
    el.classList.toggle('error', isError);
    el.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove('show'), 2200);
}

async function apiGet() {
    const r = await fetch(API);
    if (r.status === 401) { location.href = 'login.php'; return null; }
    if (!r.ok) throw new Error('GET failed: ' + r.status);
    return await r.json();
}

async function apiSave() {
    const r = await fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(state),
    });
    if (r.status === 401) { location.href = 'login.php'; return false; }
    if (!r.ok) { toast(t('toast.error'), true); return false; }
    toast(t('toast.saved'));
    return true;
}

function debounce(fn, ms) {
    let tmr = null;
    return (...a) => { clearTimeout(tmr); tmr = setTimeout(() => fn(...a), ms); };
}
const saveDebounced = debounce(apiSave, 400);

// ---------- Rendering ----------
function applyI18nStatic() {
    $$('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const val = t(key);
        if (val) el.textContent = val;
    });
    $('#lang-toggle').textContent = lang === 'en' ? '🇬🇧 EN' : '🇷🇺 RU';
    document.documentElement.lang = lang;
}

function renderRoadmap() {
    const container = $('#milestones');
    if (!state) return;

    // Progress summary
    let total = 0, done = 0;
    state.milestones.forEach(m => m.tasks.forEach(ts => {
        total++;
        if (ts.status === 'done') done++;
    }));
    const pct = total ? Math.round((done/total)*100) : 0;
    $('#progress-summary').innerHTML = `
        <div><strong>${done} / ${total}</strong> ${t('progress.tasks')} (${pct}%)</div>
        <div class="progress-bar"><div style="width:${pct}%"></div></div>
    `;

    $('#roadmap-title').textContent = state.meta[`title_${lang}`] || state.meta.title_en;

    container.innerHTML = '';
    state.milestones.forEach((m, mi) => {
        const mDone = m.tasks.filter(x => x.status === 'done').length;
        const mTotal = m.tasks.length;
        const div = document.createElement('div');
        div.className = 'milestone expanded';
        div.dataset.mid = m.id;
        div.innerHTML = `
            <div class="milestone-header">
                <span class="milestone-id">${escapeHtml(m.id)}</span>
                <h3 class="milestone-title">${escapeHtml(m[`title_${lang}`] || m.title_en)}</h3>
                <span class="milestone-progress">${mDone}/${mTotal}</span>
                <span class="milestone-expand">›</span>
            </div>
            <div class="milestone-body">
                <p class="milestone-desc">${escapeHtml(m[`description_${lang}`] || m.description_en || '')}</p>
                <div class="milestone-owner">${t('label.owner')}: <strong>${escapeHtml(m.owner || '—')}</strong></div>
                <ul class="task-list"></ul>
                <div class="milestone-toolbar">
                    <button class="btn btn-ghost" data-act="add-task">${t('btn.add_task')}</button>
                    <button class="btn btn-ghost" data-act="edit-milestone">✎ ${t('label.title')}</button>
                    <button class="btn btn-ghost" data-act="delete-milestone">🗑 ${t('btn.delete')}</button>
                </div>
            </div>
        `;
        const ul = div.querySelector('.task-list');
        m.tasks.forEach((task, ti) => {
            const li = document.createElement('li');
            li.className = `task status-${task.status}`;
            li.dataset.tid = task.id;
            li.innerHTML = `
                <div class="task-row">
                    <span class="task-check" data-act="cycle-status" title="${escapeHtml(task.status)}"></span>
                    <span class="task-id">${escapeHtml(task.id)}</span>
                    <span class="task-title">${escapeHtml(task[`title_${lang}`] || task.title_en)}</span>
                    <span class="task-owner">${escapeHtml(task.owner || '—')}</span>
                    <span class="task-actions">
                        <button data-act="edit-task" title="${t('btn.save')}">✎</button>
                        <button data-act="del-task" title="${t('btn.delete')}">🗑</button>
                    </span>
                </div>
            `;
            if (task.notes) {
                const n = document.createElement('div');
                n.className = 'task-notes';
                n.textContent = task.notes;
                li.appendChild(n);
            }
            if (task.updated_by && task.updated_at) {
                const m = document.createElement('div');
                m.className = 'task-meta';
                m.textContent = `${task.updated_by} · ${timeAgo(task.updated_at)}`;
                li.appendChild(m);
            }
            const row = li.querySelector('.task-row');
            row.querySelector('[data-act="cycle-status"]').onclick = () => cycleTaskStatus(mi, ti);
            row.querySelector('[data-act="edit-task"]').onclick   = () => editTask(mi, ti);
            row.querySelector('[data-act="del-task"]').onclick    = () => delTask(mi, ti);
            ul.appendChild(li);
        });

        div.querySelector('.milestone-header').onclick = (e) => {
            if (e.target.closest('button')) return;
            div.classList.toggle('expanded');
        };
        div.querySelector('[data-act="add-task"]').onclick        = () => addTask(mi);
        div.querySelector('[data-act="edit-milestone"]').onclick  = () => editMilestone(mi);
        div.querySelector('[data-act="delete-milestone"]').onclick = () => delMilestone(mi);

        container.appendChild(div);
    });
}

function renderSchematic() {
    const wrap = $('#schem-render');
    wrap.innerHTML = `<div class="mermaid">${escapeHtml(state.schematic.mermaid_source)}</div>`;
    try {
        mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });
        mermaid.run({ nodes: wrap.querySelectorAll('.mermaid') });
    } catch (e) {
        console.error('Mermaid render error:', e);
        wrap.innerHTML = `<pre style="color:#e15453">Mermaid render error: ${escapeHtml(e.message)}</pre>`;
    }
}

function renderShopping() {
    const tbody = $('#shop-tbody');
    const filterTask = $('#shop-filter-task').value;
    const filterStatus = $('#shop-filter-status').value;

    // Populate filter-task options
    const sel = $('#shop-filter-task');
    if (sel.options.length <= 1) {
        state.milestones.forEach(m => m.tasks.forEach(ts => {
            const opt = document.createElement('option');
            opt.value = ts.id;
            opt.textContent = `${ts.id} — ${ts.title_en.slice(0, 50)}`;
            sel.appendChild(opt);
        }));
    }

    tbody.innerHTML = '';
    state.shopping_list.forEach((it, idx) => {
        if (filterTask && it.linked_task_id !== filterTask) return;
        if (filterStatus && it.status !== filterStatus) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHtml(it[`item_${lang}`] || it.item_en)}</td>
            <td>${escapeHtml(String(it.quantity ?? ''))}</td>
            <td>${it.unit_cost_eur != null ? escapeHtml(String(it.unit_cost_eur)) : '—'}</td>
            <td>${it.vendor_url ? `<a href="${escapeHtml(it.vendor_url)}" target="_blank" rel="noopener">link</a>` : '—'}</td>
            <td><code>${escapeHtml(it.linked_task_id || '—')}</code></td>
            <td><span class="shop-status ${escapeHtml(it.status)}">${escapeHtml(t('status.'+it.status) || it.status)}</span></td>
            <td>
                <button class="btn btn-ghost" data-act="edit-item">✎</button>
                <button class="btn btn-ghost" data-act="del-item">🗑</button>
            </td>
        `;
        tr.querySelector('[data-act="edit-item"]').onclick = () => editItem(idx);
        tr.querySelector('[data-act="del-item"]').onclick  = () => delItem(idx);
        tbody.appendChild(tr);
    });
    if (!tbody.children.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="muted" style="text-align:center;padding:24px">—</td></tr>`;
    }
}

function renderAll() {
    applyI18nStatic();
    renderRoadmap();
    renderShopping();
    if ($('#tab-schematic').classList.contains('active')) renderSchematic();
}

// ---------- State mutations ----------
function cycleTaskStatus(mi, ti) {
    const order = ['todo','in_progress','done','blocked'];
    const cur = state.milestones[mi].tasks[ti].status;
    const next = order[(order.indexOf(cur)+1) % order.length];
    state.milestones[mi].tasks[ti].status = next;
    renderRoadmap();
    saveDebounced();
}

function nextTaskId(mi) {
    const m = state.milestones[mi];
    const used = m.tasks.map(ts => parseInt((ts.id.split('-T')[1]||'0'),10)).filter(n=>!isNaN(n));
    const n = used.length ? Math.max(...used)+1 : 1;
    return `${m.id}-T${n}`;
}

function nextMilestoneId() {
    const nums = state.milestones.map(m => parseInt(m.id.replace('M',''),10)).filter(n=>!isNaN(n));
    return 'M' + (nums.length ? Math.max(...nums)+1 : 1);
}

function nextShopId() {
    const nums = state.shopping_list.map(it => parseInt((it.id.split('-')[1]||'0'),10)).filter(n=>!isNaN(n));
    const n = nums.length ? Math.max(...nums)+1 : 1;
    return 'S-' + String(n).padStart(3,'0');
}

function addTask(mi) {
    openModal(t('btn.add_task'), [
        { key:'title_en', label: t('label.title_en'), type:'text', value:'' },
        { key:'title_ru', label: t('label.title_ru'), type:'text', value:'' },
        { key:'owner',    label: t('label.owner'),    type:'text', value: state.milestones[mi].owner || '' },
        { key:'status',   label: t('label.status'),   type:'select', options: ['todo','in_progress','done','blocked'], value:'todo' },
        { key:'notes',    label: t('label.notes'),    type:'textarea', value:'' },
    ], (data) => {
        state.milestones[mi].tasks.push({
            id: nextTaskId(mi),
            title_en: data.title_en || '(untitled)',
            title_ru: data.title_ru || '',
            owner: data.owner || '',
            status: data.status || 'todo',
            notes: data.notes || '',
        });
        renderRoadmap(); renderShopping(); saveDebounced();
    });
}

function editTask(mi, ti) {
    const task = state.milestones[mi].tasks[ti];
    openModal(`${t('btn.edit_source')}: ${task.id}`, [
        { key:'title_en', label: t('label.title_en'), type:'text',     value: task.title_en || '' },
        { key:'title_ru', label: t('label.title_ru'), type:'text',     value: task.title_ru || '' },
        { key:'owner',    label: t('label.owner'),    type:'text',     value: task.owner || '' },
        { key:'status',   label: t('label.status'),   type:'select',   options:['todo','in_progress','done','blocked'], value: task.status },
        { key:'notes',    label: t('label.notes'),    type:'textarea', value: task.notes || '' },
    ], (data) => {
        Object.assign(task, data);
        renderRoadmap(); saveDebounced();
    });
}

function delTask(mi, ti) {
    if (!confirm(t('confirm.delete'))) return;
    state.milestones[mi].tasks.splice(ti,1);
    renderRoadmap(); renderShopping(); saveDebounced();
}

function addMilestone() {
    openModal(t('btn.add_milestone'), [
        { key:'title_en',        label: t('label.title_en'),    type:'text', value:'' },
        { key:'title_ru',        label: t('label.title_ru'),    type:'text', value:'' },
        { key:'description_en',  label: t('label.description')+' (EN)', type:'textarea', value:'' },
        { key:'description_ru',  label: t('label.description')+' (RU)', type:'textarea', value:'' },
        { key:'owner',           label: t('label.owner'),       type:'text', value:'' },
    ], (data) => {
        state.milestones.push({
            id: nextMilestoneId(),
            title_en: data.title_en || '(untitled)',
            title_ru: data.title_ru || '',
            description_en: data.description_en || '',
            description_ru: data.description_ru || '',
            owner: data.owner || '',
            tasks: [],
        });
        renderRoadmap(); saveDebounced();
    });
}

function editMilestone(mi) {
    const m = state.milestones[mi];
    openModal(`${t('btn.edit_source')}: ${m.id}`, [
        { key:'title_en', label: t('label.title_en'), type:'text', value: m.title_en || '' },
        { key:'title_ru', label: t('label.title_ru'), type:'text', value: m.title_ru || '' },
        { key:'description_en', label: t('label.description')+' (EN)', type:'textarea', value: m.description_en || '' },
        { key:'description_ru', label: t('label.description')+' (RU)', type:'textarea', value: m.description_ru || '' },
        { key:'owner',    label: t('label.owner'),    type:'text', value: m.owner || '' },
    ], (data) => { Object.assign(m, data); renderRoadmap(); saveDebounced(); });
}

function delMilestone(mi) {
    if (!confirm(t('confirm.delete'))) return;
    state.milestones.splice(mi,1);
    renderRoadmap(); renderShopping(); saveDebounced();
}

function addItem() {
    const taskIds = state.milestones.flatMap(m => m.tasks.map(ts => ts.id));
    openModal(t('btn.add_item'), [
        { key:'item_en',       label: t('label.item_en'),      type:'text', value:'' },
        { key:'item_ru',       label: t('label.item_ru'),      type:'text', value:'' },
        { key:'quantity',      label: t('label.qty'),          type:'number', value:1 },
        { key:'unit_cost_eur', label: t('label.cost'),         type:'number', value:'' },
        { key:'vendor_url',    label: t('label.vendor'),       type:'text', value:'' },
        { key:'linked_task_id',label: t('label.linked'),       type:'select', options: ['', ...taskIds], value:'' },
        { key:'status',        label: t('label.status'),       type:'select', options: ['needed','ordered','in_hand','installed'], value:'needed' },
        { key:'notes',         label: t('label.notes'),        type:'textarea', value:'' },
    ], (data) => {
        state.shopping_list.push({
            id: nextShopId(),
            item_en: data.item_en || '(untitled)',
            item_ru: data.item_ru || '',
            quantity: Number(data.quantity) || 1,
            unit_cost_eur: data.unit_cost_eur === '' || data.unit_cost_eur == null ? null : Number(data.unit_cost_eur),
            vendor_url: data.vendor_url || '',
            linked_task_id: data.linked_task_id || '',
            status: data.status || 'needed',
            notes: data.notes || '',
        });
        renderShopping(); saveDebounced();
    });
}

function editItem(idx) {
    const it = state.shopping_list[idx];
    const taskIds = state.milestones.flatMap(m => m.tasks.map(ts => ts.id));
    openModal(`${t('btn.edit_source')}: ${it.id}`, [
        { key:'item_en',       label: t('label.item_en'),      type:'text', value: it.item_en || '' },
        { key:'item_ru',       label: t('label.item_ru'),      type:'text', value: it.item_ru || '' },
        { key:'quantity',      label: t('label.qty'),          type:'number', value: it.quantity ?? 1 },
        { key:'unit_cost_eur', label: t('label.cost'),         type:'number', value: it.unit_cost_eur ?? '' },
        { key:'vendor_url',    label: t('label.vendor'),       type:'text', value: it.vendor_url || '' },
        { key:'linked_task_id',label: t('label.linked'),       type:'select', options: ['', ...taskIds], value: it.linked_task_id || '' },
        { key:'status',        label: t('label.status'),       type:'select', options: ['needed','ordered','in_hand','installed'], value: it.status },
        { key:'notes',         label: t('label.notes'),        type:'textarea', value: it.notes || '' },
    ], (data) => {
        it.item_en = data.item_en;
        it.item_ru = data.item_ru;
        it.quantity = Number(data.quantity) || 1;
        it.unit_cost_eur = data.unit_cost_eur === '' || data.unit_cost_eur == null ? null : Number(data.unit_cost_eur);
        it.vendor_url = data.vendor_url || '';
        it.linked_task_id = data.linked_task_id || '';
        it.status = data.status;
        it.notes = data.notes || '';
        renderShopping(); saveDebounced();
    });
}

function delItem(idx) {
    if (!confirm(t('confirm.delete'))) return;
    state.shopping_list.splice(idx,1);
    renderShopping(); saveDebounced();
}

// ---------- Modal ----------
function openModal(title, fields, onSave) {
    $('#modal-title').textContent = title;
    const body = $('#modal-body');
    body.innerHTML = '';
    fields.forEach(f => {
        const l = document.createElement('label');
        l.textContent = f.label;
        let inp;
        if (f.type === 'textarea') {
            inp = document.createElement('textarea');
            inp.value = f.value ?? '';
        } else if (f.type === 'select') {
            inp = document.createElement('select');
            (f.options || []).forEach(o => {
                const opt = document.createElement('option');
                opt.value = o; opt.textContent = o || '—';
                if (o === f.value) opt.selected = true;
                inp.appendChild(opt);
            });
        } else {
            inp = document.createElement('input');
            inp.type = f.type || 'text';
            inp.value = f.value ?? '';
        }
        inp.dataset.key = f.key;
        l.appendChild(inp);
        body.appendChild(l);
    });
    $('#modal').classList.remove('hidden');
    const firstInput = body.querySelector('input, textarea, select');
    if (firstInput) firstInput.focus();
    $('#modal-save').onclick = () => {
        const data = {};
        $$('[data-key]', body).forEach(el => { data[el.dataset.key] = el.value; });
        $('#modal').classList.add('hidden');
        onSave(data);
    };
    $('#modal-cancel').onclick = () => $('#modal').classList.add('hidden');
}

// ---------- Schematic editing ----------
function editSchematic() {
    $('#schem-source').value = state.schematic.mermaid_source;
    $('#schem-source').classList.remove('hidden');
    $('#schem-render').classList.add('hidden');
    $('#edit-schem').classList.add('hidden');
    $('#save-schem').classList.remove('hidden');
    $('#cancel-schem').classList.remove('hidden');
}
function saveSchematic() {
    state.schematic.mermaid_source = $('#schem-source').value;
    $('#schem-source').classList.add('hidden');
    $('#schem-render').classList.remove('hidden');
    $('#edit-schem').classList.remove('hidden');
    $('#save-schem').classList.add('hidden');
    $('#cancel-schem').classList.add('hidden');
    renderSchematic();
    saveDebounced();
}
function cancelSchematic() {
    $('#schem-source').classList.add('hidden');
    $('#schem-render').classList.remove('hidden');
    $('#edit-schem').classList.remove('hidden');
    $('#save-schem').classList.add('hidden');
    $('#cancel-schem').classList.add('hidden');
}

// ---------- Tabs ----------
function switchTab(name) {
    $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
    $$('.panel').forEach(p => p.classList.toggle('active', p.id === `tab-${name}`));
    if (name === 'schematic') renderSchematic();
}

// ---------- History ----------
function openHistory() {
    const entries = (state.audit_log || []).slice().reverse();
    const body = document.createElement('div');
    body.className = 'audit-list';
    if (!entries.length) {
        body.innerHTML = `<p class="muted" style="padding:14px">—</p>`;
    } else {
        entries.forEach(e => {
            const div = document.createElement('div');
            div.className = 'audit-entry';
            const when = new Date(e.ts).toLocaleString();
            const changesHtml = (e.changes || []).map(c => `<code>${escapeHtml(c)}</code>`).join(' ');
            div.innerHTML = `
                <span class="audit-when">${escapeHtml(when)}</span>
                <span class="audit-user">${escapeHtml(e.user || '?')}</span>
                <span class="audit-what">${changesHtml}</span>
            `;
            body.appendChild(div);
        });
    }
    $('#modal-title').textContent = t('btn.history');
    $('#modal-body').innerHTML = '';
    $('#modal-body').appendChild(body);
    $('#modal-save').classList.add('hidden');
    $('#modal-cancel').textContent = t('btn.close') || 'Close';
    $('#modal').classList.remove('hidden');
    $('#modal-cancel').onclick = () => {
        $('#modal').classList.add('hidden');
        $('#modal-save').classList.remove('hidden');
        $('#modal-cancel').textContent = t('btn.cancel');
    };
}

// ---------- Download ----------
function downloadJson() {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `oceanpulse_roadmap_${new Date().toISOString().slice(0,10)}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
}

// ---------- Bootstrap ----------
async function init() {
    state = await apiGet();
    if (!state) return;

    $('#lang-toggle').onclick = () => {
        lang = (lang === 'en') ? 'ru' : 'en';
        localStorage.setItem(LANG_KEY, lang);
        renderAll();
    };
    $$('.tab').forEach(btn => btn.onclick = () => switchTab(btn.dataset.tab));
    $('#add-milestone').onclick = addMilestone;
    $('#add-item').onclick       = addItem;
    $('#history-btn').onclick    = openHistory;
    $('#edit-schem').onclick     = editSchematic;
    $('#save-schem').onclick     = saveSchematic;
    $('#cancel-schem').onclick   = cancelSchematic;
    $('#shop-filter-task').onchange   = renderShopping;
    $('#shop-filter-status').onchange = renderShopping;
    $('#download-btn').onclick   = downloadJson;

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && !$('#modal').classList.contains('hidden')) {
            $('#modal').classList.add('hidden');
        }
    });

    renderAll();
}

init().catch(e => {
    console.error(e);
    toast('Failed to load: ' + e.message, true);
});

})();
