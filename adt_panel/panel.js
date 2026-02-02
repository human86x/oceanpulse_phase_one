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
    
    const content = specsContent[specRef] || specsContent[specRef + '.md'] || 'Spec content not available in ADS build.';
    const modalTitle = document.getElementById('specModalLabel');
    const modalBody = document.getElementById('specModalContent');
    
    modalTitle.textContent = 'Spec: ' + specRef;
    
    // Render Markdown using marked.js
    if (typeof marked !== 'undefined') {
        modalBody.innerHTML = marked.parse(content);
        modalBody.style.fontFamily = 'inherit';
    } else {
        modalBody.textContent = content;
        modalBody.style.fontFamily = 'monospace';
    }
    
    const modal = new bootstrap.Modal(document.getElementById('specModal'));
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
    document.getElementById('stat-escalations').textContent = data.escalations?.length || 0;

    // Update sync status
    document.getElementById('sync-status').textContent = 'Live';
    document.getElementById('sync-status').className = 'badge bg-success';
    document.getElementById('last-sync').textContent = 'Last sync: ' + formatTime(data.last_sync);

    // Update compliance gauge
    const total = (data.compliance?.authorized || 0) + (data.compliance?.unauthorized || 0);
    const percent = total > 0 ? Math.round((data.compliance.authorized / total) * 100) : 100;
    document.getElementById('compliance-percent').textContent = percent + '%';

    // Update gauge arc (126 is the full arc length)
    const arcLength = (percent / 100) * 126;
    document.getElementById('gauge-fill').setAttribute('stroke-dasharray', arcLength + ' 126');

    // Color based on compliance
    const gaugeColor = percent >= 90 ? '#00ff41' : percent >= 70 ? '#d29922' : '#f85149';
    document.getElementById('gauge-fill').setAttribute('stroke', gaugeColor);
    document.getElementById('compliance-percent').style.color = gaugeColor;
}

// Update agent activity
function updateAgentActivity(data) {
    const events = data.events || [];

    // Find last Claude event
    const lastClaude = events.filter(e => e.agent === 'CLAUDE').pop();
    if (lastClaude) {
        document.getElementById('claude-role').textContent = lastClaude.role || '-';
        document.getElementById('claude-last').textContent = formatTime(lastClaude.ts);
    }

    // Find last Gemini event
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

    if (Object.keys(specCounts).length === 0) {
        specsList.innerHTML = '<div class="text-muted text-center">No specs recorded</div>';
        return;
    }

    specsList.innerHTML = Object.entries(specCounts)
        .filter(([spec]) => spec && spec !== 'null')
        .map(([spec, count]) => `
            <div class="spec-item" onclick="showSpec('${spec}')" style="cursor: pointer;" title="View Spec">
                <span class="spec-name">${spec}</span>
                <span class="badge bg-secondary">${count}</span>
            </div>
        `).join('');
}

// Update escalations
function updateEscalations(data) {
    const escalationsList = document.getElementById('escalations-list');
    const escalations = data.escalations || [];

    if (escalations.length === 0) {
        escalationsList.innerHTML = `
            <div class="no-escalations">
                <i class="bi bi-check-circle"></i> No escalations
            </div>
        `;
        return;
    }

    escalationsList.innerHTML = escalations.map(e => `
        <div class="escalation-item">
            <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="event-agent ${e.agent?.toLowerCase()} badge bg-dark border border-secondary">${e.agent} : ${e.role}</span>
                <span class="event-time small text-muted">${formatTime(e.ts)}</span>
            </div>
            <div class="mb-1"><strong>${e.action_type}</strong></div>
            <div class="small text-muted fst-italic mb-2">"${e.rationale || 'No rationale provided'}"</div>
            <div class="d-flex gap-2">
                ${e.spec_ref ? `<span class="badge bg-secondary" style="font-size:0.7em">Spec: ${e.spec_ref}</span>` : ''}
                ${e.authority ? `<span class="badge bg-dark border border-secondary" style="font-size:0.7em">Auth: ${e.authority}</span>` : ''}
            </div>
        </div>
    `).join('');
}

// Render timeline
function renderTimeline(events) {
    const timeline = document.getElementById('timeline');

    // Filter events
    let filtered = events;
    if (currentFilter === 'file_edit') {
        filtered = events.filter(e => ['file_edit', 'file_create', 'file_delete'].includes(e.action_type));
    } else if (currentFilter === 'session') {
        filtered = events.filter(e => ['session_start', 'session_end'].includes(e.action_type));
    } else if (currentFilter === 'violation') {
        filtered = events.filter(e => !e.authorized || e.escalation);
    }

    // Sort by timestamp descending (newest first)
    filtered = filtered.sort((a, b) => new Date(b.ts) - new Date(a.ts));

    if (filtered.length === 0) {
        timeline.innerHTML = '<div class="text-center text-muted p-4">No events match filter</div>';
        return;
    }

    timeline.innerHTML = filtered.slice(0, 100).map(event => {
        const statusClass = event.escalation ? 'escalation' : (event.authorized ? 'authorized' : 'unauthorized');
        const agentClass = event.agent?.toLowerCase() || '';

        return `
            <div class="timeline-event ${statusClass}">
                <div class="event-header">
                    <span>
                        <span class="event-agent ${agentClass}">${event.agent || '-'}</span>
                        <span class="event-type">${event.action_type || '-'}</span>
                    </span>
                    <span class="event-time">${formatTime(event.ts)}</span>
                </div>
                <div class="event-details">
                    <strong>${event.role || '-'}</strong>: ${event.rationale || '-'}
                </div>
                ${event.spec_ref ? `<div class="event-spec">SPEC: ${event.spec_ref}</div>` : ''}
                ${event.action_data?.file ? `<div class="small text-muted">File: ${event.action_data.file}</div>` : ''}
            </div>
        `;
    }).join('');
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
                    <div class="card-header ${config.color} text-white">
                        <i class="bi ${config.icon}"></i> ${config.title} (${statusTasks.length})
                    </div>
                    <div class="card-body p-2">
                        ${statusTasks.map(t => `
                            <div class="card mb-2 bg-secondary text-white border-0">
                                <div class="card-body p-2">
                                    <h6 class="card-title text-white small mb-1">${t.title}</h6>
                                    <div class="small text-light" style="font-size: 0.8em; opacity: 0.8;">
                                        ${t.assigned_role || 'Unassigned'}
                                    </div>
                                    <div class="mt-1">
                                        <span class="badge bg-dark" onclick="showSpec('${t.spec_ref}')" style="cursor: pointer;" title="View Spec">${t.spec_ref || 'No Spec'}</span>
                                        ${t.priority === 'critical' ? '<span class="badge bg-danger">Critical</span>' : ''}
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }
    board.innerHTML = html;
}

// Render Hierarchy View
function renderHierarchy(tasks) {
    const container = document.getElementById('hierarchy-tree');
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">No hierarchy data</div>';
        return;
    }

    // Group by Spec
    const bySpec = {};
    tasks.forEach(t => {
        const spec = t.spec_ref || 'Unspecified';
        if (!bySpec[spec]) bySpec[spec] = [];
        bySpec[spec].push(t);
    });

    let html = '<div class="accordion" id="accordionHierarchy">';
    let index = 0;
    
    for (const [spec, specTasks] of Object.entries(bySpec)) {
        const id = `collapse${index}`;
        html += `
            <div class="accordion-item bg-dark border-secondary">
                <h2 class="accordion-header">
                    <button class="accordion-button collapsed bg-dark text-white" type="button" data-bs-toggle="collapse" data-bs-target="#${id}">
                        <span onclick="event.stopPropagation(); showSpec('${spec}')" style="cursor: pointer; text-decoration: underline dotted;" title="View Spec">${spec}</span> 
                        <span class="badge bg-secondary ms-2">${specTasks.length} Tasks</span>
                    </button>
                </h2>
                <div id="${id}" class="accordion-collapse collapse" data-bs-parent="#accordionHierarchy">
                    <div class="accordion-body bg-dark text-white">
                        <ul class="list-group list-group-flush">
                            ${specTasks.map(t => `
                                <li class="list-group-item bg-dark text-white border-secondary d-flex justify-content-between align-items-center">
                                    <span>
                                        <i class="bi ${t.status === 'completed' ? 'bi-check-circle text-success' : 'bi-circle'}"></i>
                                        ${t.title}
                                    </span>
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
    html += '</div>';
    container.innerHTML = html;
}

// Render Delegation Tree (Authority Flow)
function renderDelegationTree(data) {
    // Determine input source (handle both raw array or full data object)
    let tasks = [];
    let requests = [];
    
    if (Array.isArray(data)) {
        tasks = data;
    } else {
        tasks = data.tasks || [];
        requests = data.requests || [];
    }

    const container = document.getElementById('delegation-tree');
    if ((!tasks || tasks.length === 0) && (!requests || requests.length === 0)) {
        container.innerHTML = '<div class="text-center text-muted">No delegation data</div>';
        return;
    }

    // 1. Adapter: Ensure delegation object exists for Tasks
    const adaptedTasks = tasks.map(t => {
        if (t.delegation) return t;
        return {
            ...t,
            delegation: {
                delegated_by: {
                    role: t.created_by || 'Unknown',
                    agent: 'CLAUDE' // Assumption for legacy data
                },
                delegated_to: {
                    role: t.assigned_role || 'Unassigned',
                    agent: t.assigned_agent
                },
                delegated_at: t.created_at
            }
        };
    });

    // 2. Adapter: Convert Requests to "Task-like" objects for visualization
    const adaptedRequests = requests.map(r => {
        // Parse "CLAUDE:Systems_Architect" format
        const fromParts = (r.from || '').split(':');
        const toParts = (r.to || '').replace('@', '').split(':'); // Handle @Role or @Agent:Role

        return {
            title: `REQ: ${r.subject}`,
            description: r.message,
            status: (r.status || 'pending').toLowerCase().includes('completed') ? 'completed' : 'pending',
            spec_ref: 'Request', // Group under "Request" or find a way to link to spec
            delegation: {
                delegated_by: {
                    role: fromParts[1] || fromParts[0] || 'Unknown',
                    agent: fromParts.length > 1 ? fromParts[0] : 'Unknown'
                },
                delegated_to: {
                    role: toParts[1] || toParts[0] || 'All',
                    agent: toParts.length > 1 ? toParts[0] : 'Unknown'
                }
            },
            assigned_agent: toParts.length > 1 ? toParts[0] : 'Unknown', // Approximate
            is_request: true
        };
    });

    const allItems = [...adaptedTasks, ...adaptedRequests];

    // 3. Build Tree Structure: Spec -> Delegator -> Delegatee (Role) -> Tasks/Requests
    const tree = {};
    
    allItems.forEach(t => {
        const spec = t.spec_ref || 'Unspecified';
        const delegator = `${t.delegation.delegated_by.role} (${t.delegation.delegated_by.agent || '?'})`;
        const delegatee = t.delegation.delegated_to.role || 'Unassigned';
        
        if (!tree[spec]) tree[spec] = {};
        if (!tree[spec][delegator]) tree[spec][delegator] = {};
        if (!tree[spec][delegator][delegatee]) tree[spec][delegator][delegatee] = [];
        
        tree[spec][delegator][delegatee].push(t);
    });

    // 4. Render HTML
    let html = '<ul class="list-unstyled tree-view">';
    
    for (const [spec, delegators] of Object.entries(tree)) {
        html += `
            <li class="mb-3">
                <div class="tree-node spec-node text-info fw-bold" onclick="showSpec('${spec}')" style="cursor: pointer;" title="View Spec">
                    <i class="bi bi-file-earmark-text"></i> ${spec}
                </div>
                <ul class="list-unstyled ms-4 border-start border-secondary ps-3">
        `;
        
        for (const [delegator, delegatees] of Object.entries(delegators)) {
            html += `
                <li class="mb-2">
                    <div class="tree-node delegator-node text-muted small">
                        <i class="bi bi-person-up"></i> Delegated by: ${delegator}
                    </div>
                    <ul class="list-unstyled ms-4 border-start border-secondary ps-3">
            `;
            
            for (const [delegatee, roleTasks] of Object.entries(delegatees)) {
                html += `
                    <li class="mb-2">
                        <div class="tree-node role-node text-white">
                            <span class="badge bg-secondary me-2">→</span> 
                            <strong>${delegatee}</strong>
                        </div>
                        <ul class="list-unstyled ms-4 ps-1">
                `;
                
                roleTasks.forEach(t => {
                    let statusIcon = 'bi-circle';
                    let statusColor = 'text-secondary';
                    if (t.status === 'in_progress') { statusIcon = 'bi-record-circle'; statusColor = 'text-primary'; }
                    if (t.status === 'completed') { statusIcon = 'bi-check-circle-fill'; statusColor = 'text-success'; }
                    
                    const agentBadge = t.assigned_agent === 'CLAUDE' 
                        ? '<span class="badge bg-info ms-1" style="font-size:0.6em">C</span>' 
                        : t.assigned_agent === 'GEMINI'
                            ? '<span class="badge bg-warning text-dark ms-1" style="font-size:0.6em">G</span>'
                            : '';

                    const typeBadge = t.is_request
                        ? '<span class="badge bg-danger ms-1" style="font-size:0.6em">REQ</span>'
                        : '';

                    html += `
                        <li class="task-node ${statusColor} py-1" title="${t.description || ''}">
                            <i class="bi ${statusIcon}"></i> ${t.title} ${agentBadge} ${typeBadge}
                        </li>
                    `;
                    
                    // Render subtasks if any
                    if (t.subtasks && t.subtasks.length > 0) {
                         html += '<ul class="list-unstyled ms-4 border-start border-secondary ps-2">';
                         t.subtasks.forEach(st => {
                             html += `<li class="text-muted small"><i class="bi bi-arrow-return-right"></i> ${st.title}</li>`;
                         });
                         html += '</ul>';
                    }
                });
                
                html += `</ul></li>`; // End Delegatee
            }
            html += `</ul></li>`; // End Delegator
        }
        html += `</ul></li>`; // End Spec
    }
    html += '</ul>';
    
    container.innerHTML = html;
    
    // Wire up trace button
    const traceBtn = document.getElementById('btn-trace-auth');
    if (traceBtn) {
        traceBtn.onclick = () => {
             // Simple visual effect for now
             document.querySelectorAll('.border-start').forEach(el => {
                 el.classList.add('border-info');
                 setTimeout(() => el.classList.remove('border-info'), 2000);
             });
        };
    }
}

// Render Delegation Matrix (Role × Agent matrix)
function renderDelegationMatrix(tasks) {
    const container = document.getElementById('delegation-matrix');
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">No delegation data</div>';
        return;
    }

    // Define all roles and agents
    const roles = [
        'Systems_Architect',
        'Embedded_Engineer',
        'Network_Engineer',
        'Backend_Engineer',
        'Frontend_Engineer',
        'DevOps_Engineer',
        'Overseer'
    ];
    const agents = ['CLAUDE', 'GEMINI', 'UNASSIGNED'];

    // Build matrix counts
    const matrix = {};
    roles.forEach(role => {
        matrix[role] = { CLAUDE: [], GEMINI: [], UNASSIGNED: [] };
    });

    // Populate matrix with tasks
    tasks.forEach(task => {
        const role = task.assigned_role || 'Unassigned';
        const agent = task.assigned_agent || 'UNASSIGNED';
        if (matrix[role] && matrix[role][agent] !== undefined) {
            matrix[role][agent].push(task);
        }
    });

    // Build HTML table
    let html = `
        <div class="table-responsive">
            <table class="table table-dark table-bordered">
                <thead>
                    <tr>
                        <th class="text-center">Role</th>
                        <th class="text-center"><span class="badge bg-info">CLAUDE</span></th>
                        <th class="text-center"><span class="badge bg-warning text-dark">GEMINI</span></th>
                        <th class="text-center"><span class="badge bg-secondary">UNASSIGNED</span></th>
                        <th class="text-center">Total</th>
                    </tr>
                </thead>
                <tbody>
    `;

    roles.forEach(role => {
        const claudeTasks = matrix[role].CLAUDE;
        const geminiTasks = matrix[role].GEMINI;
        const unassignedTasks = matrix[role].UNASSIGNED;
        const total = claudeTasks.length + geminiTasks.length + unassignedTasks.length;

        // Skip roles with no tasks
        if (total === 0) return;

        const roleName = role.replace(/_/g, ' ');

        html += `
            <tr>
                <td><strong>${roleName}</strong></td>
                <td class="text-center">${renderDelegationCell(claudeTasks, 'info')}</td>
                <td class="text-center">${renderDelegationCell(geminiTasks, 'warning')}</td>
                <td class="text-center">${renderDelegationCell(unassignedTasks, 'secondary')}</td>
                <td class="text-center"><span class="badge bg-light text-dark">${total}</span></td>
            </tr>
        `;
    });

    // Add totals row
    const totalClaude = tasks.filter(t => t.assigned_agent === 'CLAUDE').length;
    const totalGemini = tasks.filter(t => t.assigned_agent === 'GEMINI').length;
    const totalUnassigned = tasks.filter(t => !t.assigned_agent).length;

    html += `
                    <tr class="table-active">
                        <td><strong>TOTAL</strong></td>
                        <td class="text-center"><span class="badge bg-info">${totalClaude}</span></td>
                        <td class="text-center"><span class="badge bg-warning text-dark">${totalGemini}</span></td>
                        <td class="text-center"><span class="badge bg-secondary">${totalUnassigned}</span></td>
                        <td class="text-center"><span class="badge bg-light text-dark">${tasks.length}</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
    `;

    // Add legend
    html += `
        <div class="mt-3 small text-muted">
            <i class="bi bi-info-circle"></i> Click on task counts to see task titles.
            Status: <span class="text-success">●</span> Completed
            <span class="text-primary">●</span> In Progress
            <span class="text-secondary">●</span> Pending
        </div>
    `;

    container.innerHTML = html;
}

// Helper to render delegation cell with task details
function renderDelegationCell(tasks, colorClass) {
    if (tasks.length === 0) return '<span class="text-muted">-</span>';

    const completed = tasks.filter(t => t.status === 'completed').length;
    const inProgress = tasks.filter(t => t.status === 'in_progress').length;
    const pending = tasks.filter(t => t.status === 'pending').length;

    // Create tooltip with task titles
    const titles = tasks.map(t => {
        const icon = t.status === 'completed' ? '✓' : t.status === 'in_progress' ? '●' : '○';
        return `${icon} ${t.title}`;
    }).join('\n');

    return `
        <span class="badge bg-${colorClass} ${colorClass === 'warning' ? 'text-dark' : ''}"
              style="cursor: pointer"
              title="${titles.replace(/"/g, '&quot;')}"
              data-bs-toggle="tooltip">
            ${tasks.length}
            <small class="ms-1">(${completed}/${inProgress}/${pending})</small>
        </span>
    `;
}

// Format timestamp
function formatTime(ts) {
    if (!ts) return '-';
    const date = new Date(ts);
    return date.toLocaleString('en-GB', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Initialize filter buttons
function initFilters() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderTimeline(allEvents);
        });
    });
}

// Main initialization
async function init() {
    const data = await fetchData();

    if (!data) {
        document.getElementById('sync-status').textContent = 'Error';
        document.getElementById('sync-status').className = 'badge bg-danger';
        return;
    }

    allEvents = data.events || [];
    const allTasks = data.tasks || [];

    updateStats(data);
    updateAgentActivity(data);
    updateSpecs(data);
    updateEscalations(data);
    renderTimeline(allEvents);
    renderTasks(allTasks);
    renderHierarchy(allTasks);
    renderDelegationMatrix(allTasks);
    renderDelegationTree(data);
    initFilters();

    // Initialize Bootstrap tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));

    // Auto-refresh every 30 seconds
    setInterval(async () => {
        const newData = await fetchData();
        if (newData) {
            allEvents = newData.events || [];
            const newTasks = newData.tasks || [];
            updateStats(newData);
            updateAgentActivity(newData);
            updateSpecs(newData);
            updateEscalations(newData);
            renderTimeline(allEvents);
            renderTasks(newTasks);
            renderHierarchy(newTasks);
            renderDelegationMatrix(newTasks);
            renderDelegationTree(newData);
        }
    }, 30000);
}

// Start
document.addEventListener('DOMContentLoaded', init);
