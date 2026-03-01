/**
 * ADT Oversight Panel - JavaScript
 * Reads from data.json (compiled from ADS events.jsonl)
 *
 * Per ADT Framework (Sheridan, 2026):
 * "All stakeholders operate from the same factual, verifiable information."
 */

let allEvents = [];
let specsContent = {};
let currentFilter = 'all';

// Show Spec Modal
window.showSpec = function(specRef) {
    if (!specRef || specRef === 'null' || specRef === 'No Spec') return;
    
    let lookupKey = specRef;
    if (/^\d{3}$/.test(specRef)) lookupKey = 'SPEC-' + specRef;

    const content = specsContent[lookupKey] || specsContent[specRef] || specsContent[specRef + '.md'] || 'Spec content not available in ADS build.';
    const modalTitle = document.getElementById('specModalLabel');
    const modalBody = document.getElementById('specModalContent');
    
    modalTitle.textContent = 'Spec: ' + lookupKey;
    
    if (typeof marked !== 'undefined' && content !== 'Spec content not available in ADS build.') {
        modalBody.innerHTML = marked.parse(content);
        modalBody.style.fontFamily = 'inherit';
        modalBody.style.whiteSpace = 'normal';
    } else {
        modalBody.textContent = content;
        modalBody.style.fontFamily = 'monospace';
        modalBody.style.whiteSpace = 'pre-wrap';
    }
    
    const modalEl = document.getElementById('specModal');
    let modal = bootstrap.Modal.getInstance(modalEl);
    if (!modal) {
        modal = new bootstrap.Modal(modalEl, {
            keyboard: true,
            backdrop: true
        });
    }
    modal.show();
}

// Show Event Modal
window.showEvent = function(eventId) {
    if (!eventId) return;
    
    const event = allEvents.find(e => e.id === eventId);
    if (!event) {
        alert('Event ID not found: ' + eventId);
        return;
    }
    
    const modalTitle = document.getElementById('eventModalLabel');
    const modalBody = document.getElementById('eventModalContent');
    
    modalTitle.textContent = 'Event: ' + eventId;
    modalBody.textContent = JSON.stringify(event, null, 2);
    
    const modalEl = document.getElementById('eventModal');
    let modal = bootstrap.Modal.getInstance(modalEl);
    if (!modal) {
        modal = new bootstrap.Modal(modalEl, {
            keyboard: true,
            backdrop: true
        });
    }
    modal.show();
}

// Fetch data from ADS (compiled)
async function fetchData() {
    try {
        const response = await fetch('data.json?t=' + Date.now());
        if (!response.ok) throw new Error('Failed to load ADS data');
        const data = await response.json();
        specsContent = data.specs_content || {};
        return data;
    } catch (error) {
        console.error('Error fetching ADS data:', error);
        return null;
    }
}

// Update stats display
function updateStats(data) {
    document.getElementById('stat-total').textContent = data.total_events || 0;
    document.getElementById('stat-authorized').textContent = data.compliance?.authorized || 0;
    document.getElementById('stat-unauthorized').textContent = data.compliance?.unauthorized || 0;
    document.getElementById('stat-claude').textContent = data.by_agent?.CLAUDE || 0;
    document.getElementById('stat-gemini').textContent = data.by_agent?.GEMINI || 0;
    
    if (data.escalation_stats) {
        document.getElementById('stat-escalations-active').textContent = data.escalation_stats.active || 0;
        document.getElementById('stat-escalations-resolved').textContent = data.escalation_stats.resolved || 0;
    }

    const integrityBadge = document.getElementById('integrity-status');
    if (data.integrity) {
        if (data.integrity.chain_valid) {
            if (data.integrity.known_exceptions && data.integrity.known_exceptions.length > 0) {
                integrityBadge.innerHTML = '<i class="bi bi-shield-fill-plus"></i> LEDGER HEALED';
                integrityBadge.className = 'badge bg-info text-dark me-2';
                integrityBadge.title = "Historical exceptions: " + data.integrity.known_exceptions.join(', ');
            } else {
                integrityBadge.innerHTML = '<i class="bi bi-shield-fill-check"></i> LEDGER VERIFIED';
                integrityBadge.className = 'badge integrity-verified me-2';
            }
        } else {
            integrityBadge.innerHTML = '<i class="bi bi-shield-fill-exclamation"></i> LEDGER COMPROMISED';
            integrityBadge.className = 'badge integrity-compromised me-2';
        }
    }

    document.getElementById('sync-status').textContent = 'Live';
    document.getElementById('sync-status').className = 'badge bg-success';
    document.getElementById('last-sync').textContent = 'Last sync: ' + formatTime(data.last_sync);

    const total = (data.compliance?.authorized || 0) + (data.compliance?.unauthorized || 0);
    const percent = total > 0 ? Math.round((data.compliance.authorized / total) * 100) : 100;
    document.getElementById('compliance-percent').textContent = percent + '%';
    const arcLength = (percent / 100) * 126;
    document.getElementById('gauge-fill').setAttribute('stroke-dasharray', arcLength + ' 126');
    const gaugeColor = percent >= 90 ? '#00ff41' : percent >= 70 ? '#d29922' : '#f85149';
    document.getElementById('gauge-fill').setAttribute('stroke', gaugeColor);
    document.getElementById('compliance-percent').style.color = gaugeColor;
}

// Update agent activity
function updateAgentActivity(data) {
    const events = data.events || [];
    const lastClaude = events.filter(e => e.agent === 'CLAUDE').pop();
    if (lastClaude) {
        document.getElementById('claude-role').textContent = lastClaude.role || '-';
        document.getElementById('claude-last').textContent = formatTime(lastClaude.ts);
    }
    const lastGemini = events.filter(e => e.agent === 'GEMINI').pop();
    if (lastGemini) {
        document.getElementById('gemini-role').textContent = lastGemini.role || '-';
        document.getElementById('gemini-last').textContent = formatTime(lastGemini.ts);
    }
}

// Update specs coverage
function updateSpecs(data) {
    const specsList = document.getElementById('specs-list');
    const specCounts = data.by_spec || {};
    const content = data.specs_content || {};

    if (Object.keys(specCounts).length === 0) {
        specsList.innerHTML = '<div class="text-muted text-center">No specs recorded</div>';
        return;
    }

    specsList.innerHTML = Object.entries(specCounts)
        .filter(([spec]) => spec && spec !== 'null')
        .map(([spec, count]) => {
            const specText = content[spec] || content[spec + '.md'] || '';
            const isApproved = specText.includes('Status: APPROVED');
            const isPending = specText.includes('Status: PENDING') || specText.includes('Status: DRAFT');
            
            let icon = '<i class="bi bi-file-earmark-text text-muted"></i>';
            if (isApproved) icon = '<i class="bi bi-patch-check-fill text-success"></i>';
            else if (isPending) icon = '<i class="bi bi-clock-history text-warning"></i>';

            return `
                <div class="spec-item" onclick="showSpec('${spec}')" style="cursor: pointer;" title="View Spec">
                    <span class="spec-name">${icon} ${spec}</span>
                    <span class="badge bg-secondary">${count}</span>
                </div>
            `;
        }).join('');
}

// Update escalations
function updateEscalations(data) {
    const escalationsList = document.getElementById('escalations-list');
    const allEvents = data.events || [];
    const sourceEscalations = data.escalations || [];
    const resolvedIds = data.escalation_stats?.resolved_ids || [];
    
    const activeEscalations = sourceEscalations
        .filter(e => !resolvedIds.includes(e.id))
        .sort((a, b) => new Date(b.ts) - new Date(a.ts));
        
    const resolvedEscalations = sourceEscalations
        .filter(e => resolvedIds.includes(e.id))
        .sort((a, b) => new Date(b.ts) - new Date(a.ts));

    const sortedEscalations = [...activeEscalations, ...resolvedEscalations];

    if (sortedEscalations.length === 0) {
        escalationsList.innerHTML = `<div class="no-escalations"><i class="bi bi-check-circle"></i> No active escalations</div>`;
        return;
    }

    escalationsList.innerHTML = sortedEscalations.map(e => {
        const isResolved = resolvedIds.includes(e.id);
        const referencingEvents = allEvents.filter(r => (r.id === e.resolved_by_event_id) || (r.ref_id === e.id) || (r.action_data?.resolved_event_id === e.id));
        const latestResolver = [...referencingEvents].sort((a, b) => new Date(b.ts) - new Date(a.ts))[0];
        
        let resolutionHtml = '';
        if (isResolved && latestResolver) {
            resolutionHtml = `<div class="resolution-box p-2 mt-2 mb-1" style="font-size: 0.85em;"><strong>Resolved:</strong> ${latestResolver.rationale}</div>`;
        }
        
        return `
            <div class="escalation-item ${isResolved ? 'escalation-resolved' : ''} mb-3 shadow-sm">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="badge bg-dark border border-secondary">${e.agent} : ${e.role}</span>
                    <span class="small text-muted">${formatTime(e.ts)}</span>
                </div>
                <strong class="${isResolved ? 'text-success' : 'text-danger'}" onclick="showEvent('${e.id}')" style="cursor: pointer;">
                    ${isResolved ? 'RESOLVED: ' : 'ESCALATION: '}${e.action_type}
                </strong>
                <div class="small opacity-75 fst-italic mb-2">${e.rationale}</div>
                ${resolutionHtml}
            </div>
        `;
    }).join('');
}

// Render timeline
function renderTimeline(events) {
    const timeline = document.getElementById('timeline');
    let filtered = events;
    if (currentFilter === 'file_edit') filtered = events.filter(e => ['file_edit', 'file_create', 'file_delete'].includes(e.action_type));
    else if (currentFilter === 'session') filtered = events.filter(e => ['session_start', 'session_end'].includes(e.action_type));
    else if (currentFilter === 'violation') filtered = events.filter(e => !e.authorized || e.escalation);

    filtered = filtered.sort((a, b) => new Date(b.ts) - new Date(a.ts));
    if (filtered.length === 0) { timeline.innerHTML = '<div class="text-center text-muted p-4">No events match filter</div>'; return; }

    timeline.innerHTML = filtered.slice(0, 100).map(event => `
        <div class="timeline-event ${event.escalation ? 'escalation' : (event.authorized ? 'authorized' : 'unauthorized')}">
            <div class="event-header">
                <span><span class="event-agent ${event.agent?.toLowerCase()}">${event.agent}</span> <span class="event-type">${event.action_type}</span></span>
                <span class="event-time">${formatTime(event.ts)}</span>
            </div>
            <div class="event-details"><strong>${event.role}</strong>: ${event.rationale}</div>
        </div>
    `).join('');
}

// Render Task Board
function renderTasks(tasks) {
    const board = document.getElementById('task-board');
    if (!tasks || tasks.length === 0) {
        board.innerHTML = '<div class="col-12 text-center text-muted">No tasks found</div>';
        return;
    }

    const columns = {
        pending: { title: 'Pending', icon: 'bi-hourglass', color: 'bg-secondary' },
        in_progress: { title: 'In Progress', icon: 'bi-gear-wide-connected', color: 'bg-primary' },
        completed: { title: 'Completed', icon: 'bi-check-circle-fill', color: 'bg-success' }
    };

    let html = '';
    for (const [status, config] of Object.entries(columns)) {
        const statusTasks = tasks.filter(t => t.status === status);
        html += `
            <div class="col-md-4">
                <div class="card h-100 bg-dark border-secondary">
                    <div class="card-header ${config.color} text-white py-2">
                        <i class="bi ${config.icon}"></i> ${config.title} (${statusTasks.length})
                    </div>
                    <div class="card-body p-2" id="column-${status}">
        `;

        if (status === 'completed') {
            const byRole = {};
            statusTasks.forEach(t => {
                const role = t.assigned_role || 'Unassigned';
                if (!byRole[role]) byRole[role] = [];
                byRole[role].push(t);
            });

            html += `<div class="accordion accordion-flush" id="completedAccordion">`;
            Object.entries(byRole).forEach(([role, roleTasks], index) => {
                const safeRole = String(role).replace(/\s+/g, '-');
                const id = `role-${safeRole}`;
                html += `
                    <div class="accordion-item bg-transparent">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed bg-dark text-white py-2" type="button" data-bs-toggle="collapse" data-bs-target="#${id}">
                                <small>${role} (${roleTasks.length})</small>
                            </button>
                        </h2>
                        <div id="${id}" class="accordion-collapse collapse" data-bs-parent="#completedAccordion">
                            <div class="accordion-body p-1">
                                ${roleTasks.map(t => renderTaskCard(t)).join('')}
                            </div>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        } else {
            html += statusTasks.map(t => renderTaskCard(t)).join('');
        }
        html += `</div></div></div>`;
    }
    board.innerHTML = html;
}

function renderTaskCard(t) {
    return `
        <div class="card mb-2 bg-secondary text-white border-0 shadow-sm">
            <div class="card-body p-2">
                <h6 class="card-title text-white small mb-1">${t.title}</h6>
                <div class="small text-light" style="font-size: 0.8em; opacity: 0.8;">${t.assigned_role || 'Unassigned'}</div>
                <div class="mt-1">
                    <span class="badge bg-dark" onclick="showSpec('${t.spec_ref}')" style="cursor: pointer;">${t.spec_ref || 'No Spec'}</span>
                    ${t.priority === 'critical' ? '<span class="badge bg-danger">Critical</span>' : ''}
                </div>
            </div>
        </div>
    `;
}

// Render Hierarchy View
function renderHierarchy(tasks, specs_content = {}) {
    const container = document.getElementById('hierarchy-tree');
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">No hierarchy data</div>';
        return;
    }

    const bySpec = {};
    tasks.forEach(t => {
        const spec = t.spec_ref || 'Unspecified';
        if (!bySpec[spec]) bySpec[spec] = [];
        bySpec[spec].push(t);
    });

    let html = '<div class="accordion" id="accordionHierarchy">';
    let index = 0;
    for (const [spec, specTasks] of Object.entries(bySpec)) {
        const specText = (specs_content || {})[spec] || (specs_content || {})[spec + '.md'] || '';
        const isApproved = specText.includes('Status: APPROVED');
        const isPending = specText.includes('Status: PENDING') || specText.includes('Status: DRAFT');
        
        let icon = '<i class="bi bi-file-earmark-text text-muted me-1"></i>';
        if (isApproved) icon = '<i class="bi bi-patch-check-fill text-success me-1"></i>';
        else if (isPending) icon = '<i class="bi bi-clock-history text-warning me-1"></i>';

        const id = `collapseH-${index}`;
        html += `
            <div class="accordion-item bg-dark border-secondary">
                <h2 class="accordion-header">
                    <button class="accordion-button collapsed bg-dark text-white py-2" type="button" data-bs-toggle="collapse" data-bs-target="#${id}">
                        ${icon} <span onclick="event.stopPropagation(); showSpec('${spec}')" style="text-decoration: underline dotted;">${spec}</span> 
                        <span class="badge bg-secondary ms-2">${specTasks.length}</span>
                    </button>
                </h2>
                <div id="${id}" class="accordion-collapse collapse" data-bs-parent="#accordionHierarchy">
                    <div class="accordion-body bg-dark text-white p-2">
                        <ul class="list-group list-group-flush">
                            ${specTasks.map(t => `
                                <li class="list-group-item bg-dark text-white border-secondary d-flex justify-content-between align-items-center py-1">
                                    <small><i class="bi ${t.status === 'completed' ? 'bi-check-circle text-success' : 'bi-circle'}"></i> ${t.title}</small>
                                    <small class="text-muted">${t.assigned_role}</small>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        `;
        index++;
    }
    container.innerHTML = html + '</div>';
}

// Render Delegation Tree
function renderDelegationTree(data) {
    const tasks = data.tasks || [];
    const requests = data.requests || [];
    const container = document.getElementById('delegation-tree');
    if (tasks.length === 0 && requests.length === 0) { container.innerHTML = '<div class="text-center text-muted">No delegation data</div>'; return; }

    const allItems = [];
    
    // Process Tasks and Subtasks
    tasks.forEach(t => {
        // Main Task
        allItems.push({
            title: t.title,
            status: t.status,
            spec_ref: t.spec_ref,
            from: t.delegation?.delegated_by?.role || t.created_by || 'Systems_Architect',
            to: t.delegation?.delegated_to?.role || t.assigned_role || 'Unassigned'
        });
        
        // Subtasks
        if (t.subtasks && t.subtasks.length > 0) {
            t.subtasks.forEach(st => {
                allItems.push({
                    title: `↳ ${st.title}`,
                    status: st.status,
                    spec_ref: t.spec_ref,
                    from: st.delegation?.delegated_by?.role || t.assigned_role || 'Unassigned',
                    to: st.delegation?.delegated_to?.role || st.assigned_role || 'Unassigned'
                });
            });
        }
    });

    // Process Requests
    requests.forEach(r => {
        const fromParts = (r.from || '').split(':');
        const toParts = (r.to || '').replace('@', '').split(':');
        allItems.push({
            title: `REQ: ${r.subject}`,
            status: (r.status || '').toLowerCase().includes('completed') ? 'completed' : 'pending',
            spec_ref: 'Request',
            from: fromParts[1] || fromParts[0] || 'Unknown',
            to: toParts[1] || toParts[0] || 'All'
        });
    });

    const tree = {};
    allItems.forEach(t => {
        const spec = t.spec_ref || 'Unspecified';
        const from = String(t.from || 'Unknown');
        const to = String(t.to || 'Unassigned');
        if (!tree[spec]) tree[spec] = {};
        if (!tree[spec][from]) tree[spec][from] = {};
        if (!tree[spec][from][to]) tree[spec][from][to] = [];
        tree[spec][from][to].push(t);
    });

    let html = '<ul class="list-unstyled tree-view">';
    for (const [spec, delegators] of Object.entries(tree)) {
        html += `<li class="mb-3"><div class="text-info fw-bold" onclick="showSpec('${spec}')" style="cursor:pointer;"><i class="bi bi-file-earmark-text"></i> ${spec}</div><ul class="list-unstyled ms-3 border-start border-secondary ps-2">`;
        for (const [from, delegatees] of Object.entries(delegators)) {
            html += `<li class="mb-2"><div class="small text-muted"><i class="bi bi-person-up"></i> From: ${from}</div><ul class="list-unstyled ms-3 border-start border-secondary ps-2">`;
            for (const [to, roleTasks] of Object.entries(delegatees)) {
                html += `<li class="mb-1"><div><span class="badge bg-secondary me-1">→</span> <strong>${to}</strong></div><ul class="list-unstyled ms-3">`;
                roleTasks.forEach(item => {
                    const icon = item.status === 'completed' ? 'bi-check-circle-fill text-success' : 'bi-circle text-primary';
                    html += `<li class="small py-1"><i class="bi ${icon}"></i> ${item.title}</li>`;
                });
                html += `</ul></li>`;
            }
            html += `</ul></li>`;
        }
        html += `</ul></li>`;
    }
    container.innerHTML = html + '</ul>';
}

// Render Workflow
function renderWorkflow(events, roleFilter = 'All') {
    const container = document.getElementById('workflow-container');
    const filterContainer = document.getElementById('workflow-role-filter');
    const rawSessions = {};
    const roles = new Set();
    const sortedAll = [...events].sort((a, b) => new Date(a.ts) - new Date(b.ts));
    
    sortedAll.forEach(e => {
        if (!e.session_id || !e.role) return;
        roles.add(e.role);
        if (!rawSessions[e.session_id]) { rawSessions[e.session_id] = { id: e.session_id, events: [], startTime: e.ts, role: e.role, agent: e.agent }; }
        rawSessions[e.session_id].events.push(e);
    });

    if (filterContainer.children.length === 0) {
        let filterHtml = `<button type="button" class="btn btn-outline-light active" onclick="filterWorkflow('All', this)">All</button>`;
        Array.from(roles).sort().forEach(role => { filterHtml += `<button type="button" class="btn btn-outline-light" onclick="filterWorkflow('${role}', this)">${role}</button>`; });
        filterContainer.innerHTML = filterHtml;
    }

    let sessionList = Object.values(rawSessions).sort((a, b) => new Date(a.startTime) - new Date(b.startTime));
    if (roleFilter !== 'All') sessionList = sessionList.filter(s => s.role === roleFilter);
    
    container.innerHTML = sessionList.map(session => {
        const nodes = session.events.map(e => `<div class="flow-node ${e.escalation ? 'problem' : 'action'}"><div class="node-content" onclick="showEvent('${e.id}')"><strong>${e.action_type}</strong>: ${e.rationale}</div></div>`).join('');
        return `<div class="story-card"><div class="story-header"><span class="badge bg-secondary">${session.agent}</span> <strong>${session.role}</strong></div><div class="story-flow">${nodes}</div></div>`;
    }).join('');

    setTimeout(() => { container.scrollTop = container.scrollHeight; }, 100);
}

window.filterWorkflow = function(role, btnElement) {
    document.querySelectorAll('#workflow-role-filter .btn').forEach(b => b.classList.remove('active'));
    btnElement.classList.add('active');
    renderWorkflow(allEvents, role);
}

function formatTime(ts) { if (!ts) return '-'; const date = new Date(ts); return date.toLocaleString('en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }

function initFilters() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderTimeline(allEvents);
        });
    });
    const workflowsTab = document.getElementById('workflows-tab');
    if (workflowsTab) { workflowsTab.addEventListener('shown.bs.tab', () => { document.getElementById('workflow-container').scrollTop = 1000000; }); }
}

async function init() {
    const data = await fetchData();
    if (!data) return;
    allEvents = data.events || [];
    updateStats(data);
    updateAgentActivity(data);
    updateSpecs(data);
    updateEscalations(data);
    renderTimeline(allEvents);
    renderTasks(data.tasks || []);
    renderHierarchy(data.tasks || [], data.specs_content);
    renderDelegationTree(data);
    renderWorkflow(allEvents);
    initFilters();
}

document.addEventListener('DOMContentLoaded', init);
setInterval(async () => {
    const newData = await fetchData();
    if (newData) {
        allEvents = newData.events || [];
        updateStats(newData);
        updateAgentActivity(newData);
        updateSpecs(newData);
        updateEscalations(newData);
        renderTimeline(allEvents);
        renderTasks(newData.tasks || []);
        renderHierarchy(newData.tasks || [], newData.specs_content);
        renderDelegationTree(newData);
        renderWorkflow(allEvents);
    }
}, 30000);