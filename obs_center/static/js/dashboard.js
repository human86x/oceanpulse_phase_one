// OceanPulse Dashboard Logic

// --- Access Gate & Session (SPEC-028) ---

let currentRole = null; // 'guest' or 'admin'

function authHeaders() {
    const token = localStorage.getItem('op_token');
    if (token) return { 'X-Auth-Token': token };
    return {};
}

function authFetch(url, opts) {
    opts = opts || {};
    opts.headers = Object.assign(opts.headers || {}, authHeaders());
    return fetch(url, opts);
}

function checkSession() {
    // Try localStorage token first (survives Tailscale Funnel cookie issues)
    const savedToken = localStorage.getItem('op_token');
    const savedUser = localStorage.getItem('op_user');
    const savedRole = localStorage.getItem('op_role');
    if (savedToken && savedUser && savedRole) {
        enterPanel(savedUser, savedRole);
        return;
    }

    authFetch('/api/session')
        .then(r => r.json())
        .then(data => {
            if (data.user) {
                enterPanel(data.user, data.role);
            } else {
                showGate();
            }
        })
        .catch(() => showGate());
}

function showGate() {
    document.getElementById('access-gate').style.display = 'flex';
}

function hideGate() {
    const g = document.getElementById('access-gate');
    g.style.opacity = '0';
    setTimeout(() => { g.style.display = 'none'; }, 400);
}

function enterPanel(user, role) {
    currentRole = role;
    hideGate();

    document.getElementById('session-badge').style.display = 'inline-block';
    document.getElementById('session-user').textContent = user;

    if (role === 'admin') {
        document.getElementById('session-badge').className = 'badge bg-info me-2';
        document.getElementById('btn-logout').style.display = 'inline-block';
        document.getElementById('btn-login').style.display = 'none';
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.opacity = '1';
            el.style.pointerEvents = 'auto';
        });
    } else {
        document.getElementById('session-badge').className = 'badge bg-dark border border-secondary me-2';
        document.getElementById('btn-logout').style.display = 'none';
        document.getElementById('btn-login').style.display = 'inline-block';
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.opacity = '0.3';
            el.style.pointerEvents = 'none';
        });
    }
}

function gateGuest() {
    fetch('/api/guest', { method: 'POST' })
        .then(r => r.json())
        .then(data => enterPanel('guest', 'guest'));
}

function gateShowLogin() {
    document.getElementById('gate-buttons').style.display = 'none';
    document.getElementById('gate-login').style.display = 'block';
    document.getElementById('gate-user').focus();
}

function gateBack() {
    document.getElementById('gate-login').style.display = 'none';
    document.getElementById('gate-buttons').style.display = 'block';
    document.getElementById('gate-error').style.display = 'none';
}

function gateLogin() {
    const user = document.getElementById('gate-user').value;
    const pass = document.getElementById('gate-pass').value;

    fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pass })
    })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok, data }) => {
        if (ok && data.status === 'success') {
            document.getElementById('gate-error').style.display = 'none';
            if (data.token) {
                localStorage.setItem('op_token', data.token);
                localStorage.setItem('op_user', data.user);
                localStorage.setItem('op_role', data.role);
            }
            enterPanel(data.user, data.role);
        } else {
            document.getElementById('gate-error').style.display = 'block';
            document.getElementById('gate-pass').value = '';
        }
    });
}

function doLogout() {
    localStorage.removeItem('op_token');
    localStorage.removeItem('op_user');
    localStorage.removeItem('op_role');
    fetch('/api/logout', { method: 'POST' })
        .then(() => {
            currentRole = null;
            document.getElementById('session-badge').style.display = 'none';
            document.getElementById('btn-logout').style.display = 'none';
            document.getElementById('btn-login').style.display = 'none';
            document.getElementById('access-gate').style.opacity = '1';
            document.getElementById('access-gate').style.display = 'flex';
            document.getElementById('gate-buttons').style.display = 'block';
            document.getElementById('gate-login').style.display = 'none';
        });
}

function doLoginFromGuest() {
    localStorage.removeItem('op_token');
    localStorage.removeItem('op_user');
    localStorage.removeItem('op_role');
    fetch('/api/logout', { method: 'POST' })
        .then(() => {
            currentRole = null;
            document.getElementById('session-badge').style.display = 'none';
            document.getElementById('btn-login').style.display = 'none';
            document.getElementById('access-gate').style.opacity = '1';
            document.getElementById('access-gate').style.display = 'flex';
            document.getElementById('gate-buttons').style.display = 'none';
            document.getElementById('gate-login').style.display = 'block';
            document.getElementById('gate-user').focus();
        });
}

// Enter key support
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        const gate = document.getElementById('access-gate');
        if (gate && gate.style.display !== 'none') {
            const loginForm = document.getElementById('gate-login');
            if (loginForm && loginForm.style.display !== 'none') {
                gateLogin();
            }
        }
    }
});

document.addEventListener('DOMContentLoaded', () => {
    checkSession();
    // Initialize Main water-monitoring charts (EC / DO / Water Temp)
    function makeSensorChart(canvasId, label, color) {
        const el = document.getElementById(canvasId);
        if (!el) return null;
        return new Chart(el.getContext('2d'), {
            type: 'line',
            data: {
                labels: Array(60).fill(''),
                datasets: [{
                    label: label,
                    data: Array(60).fill(null),
                    borderColor: color,
                    backgroundColor: color + '1a',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.4,
                    spanGaps: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: false, grid: { color: '#333' }, ticks: { color: color } },
                    x: { display: false }
                },
                plugins: { legend: { display: false } },
                animation: { duration: 0 }
            }
        });
    }
    window.ecChart    = makeSensorChart('ecChart',    'EC (μS/cm)',  '#28a745');
    window.doChart    = makeSensorChart('doChart',    'DO (mg/L)',   '#0d6efd');
    window.wtempChart = makeSensorChart('wtempChart', 'Water Temp (°C)', '#0dcaf0');

    const loraEl = document.getElementById('loraChart');
    if (loraEl) {
        const loraCtx = loraEl.getContext('2d');
        window.loraChart = new Chart(loraCtx, {
            type: 'line',
            data: {
                labels: Array(30).fill(''),
                datasets: [{
                    label: 'RSSI',
                    data: Array(30).fill(0),
                    borderColor: '#0dcaf0',
                    backgroundColor: 'rgba(13, 202, 240, 0.1)',
                    borderWidth: 2,
                    pointRadius: 2,
                    tension: 0.4,
                    fill: true,
                    yAxisID: 'y'
                }, {
                    label: 'SNR',
                    data: Array(30).fill(0),
                    borderColor: '#ffc107',
                    borderWidth: 2,
                    pointRadius: 2,
                    tension: 0.4,
                    fill: false,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { 
                        type: 'linear',
                        display: true, 
                        position: 'left',
                        min: -140, 
                        max: -20,
                        grid: { color: '#333' },
                        ticks: { color: '#0dcaf0' },
                        title: { display: true, text: 'RSSI (dBm)', color: '#0dcaf0' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: -20,
                        max: 20,
                        grid: { drawOnChartArea: false },
                        ticks: { color: '#ffc107' },
                        title: { display: true, text: 'SNR (dB)', color: '#ffc107' }
                    },
                    x: { display: false }
                },
                plugins: { 
                    legend: { 
                        display: true,
                        labels: { color: '#fff' }
                    } 
                },
                animation: false
            }
        });
    }

    // Start Loop
    setInterval(updateTelemetry, 1000);
    setInterval(updateVisionStatus, 5000);
    setInterval(updateSafetySnapshot, 2000);
});

// --- Activity Log (SPEC-028 Section 6) ---

function loadActivityLog() {
    const hours = document.getElementById('activity-hours').value;
    authFetch('/api/activity?hours=' + hours)
        .then(r => {
            if (!r.ok) throw new Error('Admin access required');
            return r.json();
        })
        .then(data => {
            const tbody = document.getElementById('activity-tbody');
            const countBadge = document.getElementById('activity-count');
            countBadge.innerText = data.count + ' entries';

            if (!data.entries || data.entries.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No activity in this period</td></tr>';
                return;
            }

            tbody.innerHTML = '';
            data.entries.forEach(e => {
                const t = new Date(e.ts * 1000);
                const ts = t.toLocaleDateString() + ' ' + t.toLocaleTimeString();

                const actionColors = {
                    'login_success': 'text-success',
                    'login_failed': 'text-danger fw-bold',
                    'logout': 'text-warning',
                    'guest_entry': 'text-info',
                    'command': 'text-danger',
                    'uv_capture': 'text-danger fw-bold',
                    'lora_test': 'text-warning',
                    'lora_config': 'text-warning',
                    'page_view': 'text-muted'
                };
                const actionClass = actionColors[e.action] || 'text-white';

                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="text-muted font-monospace">${ts}</td>
                    <td class="font-monospace">${e.ip || '—'}</td>
                    <td><span class="badge ${e.role === 'admin' ? 'bg-info' : 'bg-secondary'}">${e.user}</span></td>
                    <td class="text-muted">${e.role}</td>
                    <td class="${actionClass}">${e.action}</td>
                    <td class="text-muted">${e.detail || '—'}</td>
                `;
                tbody.appendChild(row);
            });
        })
        .catch(err => {
            document.getElementById('activity-tbody').innerHTML =
                '<tr><td colspan="6" class="text-center text-danger py-4">Access denied or error: ' + err.message + '</td></tr>';
        });
}

// Auto-load activity log when tab is shown
document.addEventListener('DOMContentLoaded', () => {
    const actTab = document.getElementById('activity-tab');
    if (actTab) {
        actTab.addEventListener('shown.bs.tab', () => loadActivityLog());
    }
});

// VISION STATE

// Tab resizing fix + config loading
document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tabEl => {
    tabEl.addEventListener('shown.bs.tab', (e) => {
        if (window.ecChart) window.ecChart.resize();
        if (window.doChart) window.doChart.resize();
        if (window.wtempChart) window.wtempChart.resize();
        if (window.loraChart) window.loraChart.resize();
        // Load detection config when Vision tab opens
        if (e.target.id === 'vision-tab') loadDetectionConfig();
    });
});

function updateTelemetry() {
    fetch('/api/telemetry')
        .then(res => res.json())
        .then(data => updateUI(data))
        .catch(err => {
            console.error("Telemetry Error:", err);
            document.getElementById('conn-main').className = "badge bg-danger";
            document.getElementById('conn-main').innerText = "OFFLINE";
        });
}

function calculateLQI(rssi, snr) {
    // Basic LQI estimation: RSSI -120 to -40 (0-100), SNR -10 to +10 (0-100)
    let rssiScore = Math.min(100, Math.max(0, (rssi + 120) * 1.25));
    let snrScore = Math.min(100, Math.max(0, (snr + 10) * 5));
    return Math.round((rssiScore * 0.7) + (snrScore * 0.3));
}

function updateUI(data) {
    // Heartbeat Pulse
    const brand = document.querySelector('.navbar-brand');
    if (brand) {
        brand.style.opacity = brand.style.opacity === '0.5' ? '1' : '0.5';
    }

    // Update Main System — EC / DO / Water Temp
    document.getElementById('val-ec').innerText    = (data.main.ec != null ? data.main.ec : "--.-");
    document.getElementById('val-do').innerText    = (data.main.do != null ? data.main.do : "--.-");
    document.getElementById('val-wtemp').innerText = (data.main.water_temp != null ? data.main.water_temp : "--.-");
    // REQ-055: val-volt removed from Health card (fake firmware constant).
    // Real battery V is now in the Power card via SmartShunt.

    const relayBadge = document.getElementById('val-relay');
    relayBadge.innerText = data.main.relay || "OFF";
    relayBadge.className = data.main.relay === "ON" 
        ? "badge bg-success p-2 mb-2 shadow-sm" 
        : "badge bg-secondary p-2 mb-2";

    // Update LoRa Status & Diagnostics
    const lora = data.lora;
    if (lora) {
        const isConnected = lora.connected;
        document.getElementById('val-rssi').innerText = (lora.last_rssi ? lora.last_rssi + " dBm" : "--- dBm");
        document.getElementById('val-snr').innerText = (lora.last_snr ? lora.last_snr + " dB" : "--- dB");
        
        // Progress Bars
        const rssiPerc = lora.last_rssi ? Math.min(100, Math.max(0, (lora.last_rssi + 140) * 0.83)) : 0;
        const pbRssi = document.getElementById('pb-rssi');
        pbRssi.style.width = rssiPerc + "%";
        
        // Color code RSSI
        if (lora.last_rssi > -90) pbRssi.className = "progress-bar bg-success";
        else if (lora.last_rssi > -120) pbRssi.className = "progress-bar bg-warning";
        else pbRssi.className = "progress-bar bg-danger";
        
        const snrPerc = lora.last_snr ? Math.min(100, Math.max(0, (lora.last_snr + 20) * 2.5)) : 0;
        const pbSnr = document.getElementById('pb-snr');
        pbSnr.style.width = snrPerc + "%";
        
        // Color code SNR
        if (lora.last_snr > 5) pbSnr.className = "progress-bar bg-success";
        else if (lora.last_snr > -5) pbSnr.className = "progress-bar bg-warning";
        else pbSnr.className = "progress-bar bg-danger";
        
        // LQI
        const lqi = (lora.last_rssi !== undefined && lora.last_snr !== undefined) ? calculateLQI(lora.last_rssi, lora.last_snr) : 0;
        const lqiBadge = document.getElementById('val-lqi');
        lqiBadge.innerText = lqi + "%";
        lqiBadge.className = lqi > 70 ? "badge bg-success" : (lqi > 40 ? "badge bg-warning" : "badge bg-danger");

        // Update LoRa Chart
        if (lora.last_rssi !== undefined && lora.last_snr !== undefined && window.loraChart) {
            window.loraChart.data.datasets[0].data.push(lora.last_rssi);
            window.loraChart.data.datasets[0].data.shift();
            window.loraChart.data.datasets[1].data.push(lora.last_snr);
            window.loraChart.data.datasets[1].data.shift();
            window.loraChart.update();
        }
    }

    // Update Main charts
    function pushChart(chart, val) {
        if (!chart) return;
        const v = (typeof val === 'number' && !isNaN(val)) ? val : null;
        chart.data.datasets[0].data.push(v);
        chart.data.datasets[0].data.shift();
        chart.update();
    }
    pushChart(window.ecChart,    parseFloat(data.main.ec));
    pushChart(window.doChart,    parseFloat(data.main.do_mgL != null ? data.main.do_mgL : data.main.do));
    pushChart(window.wtempChart, parseFloat(data.main.water_temp));

    // Update Health System — SHT3x reference + 3 DHT11 sensors
    const fmtT = (v) => (v != null ? parseFloat(v).toFixed(1) + "°C" : "--.-°C");
    const fmtH = (v) => (v != null ? parseFloat(v).toFixed(0) + "%" : "--%");
    document.getElementById('val-temp').innerText  = fmtT(data.health.temp);
    document.getElementById('val-humid').innerText = fmtH(data.health.hum);
    document.getElementById('val-dht1-t').innerText = fmtT(data.health.dht1_temp);
    document.getElementById('val-dht1-h').innerText = fmtH(data.health.dht1_hum);
    document.getElementById('val-dht2-t').innerText = fmtT(data.health.dht2_temp);
    document.getElementById('val-dht2-h').innerText = fmtH(data.health.dht2_hum);
    document.getElementById('val-dht3-t').innerText = fmtT(data.health.dht3_temp);
    document.getElementById('val-dht3-h').innerText = fmtH(data.health.dht3_hum);
    document.getElementById('val-dht4-t').innerText = fmtT(data.health.dht4_temp);
    document.getElementById('val-dht4-h').innerText = fmtH(data.health.dht4_hum);
    document.getElementById('val-uptime').innerText = data.health.uptime || "N/A";

    // SPEC-036: Power card update
    updatePowerCard(data.power);

    // Update Online Indicators
    document.getElementById('conn-main').className = data.main.online ? "badge bg-success" : "badge bg-danger";
    document.getElementById('conn-main').innerText = data.main.online ? "MAIN: ONLINE" : "MAIN: OFFLINE";
    document.getElementById('conn-health').className = data.health.online ? "badge bg-success" : "badge bg-danger";
    document.getElementById('conn-health').innerText = data.health.online ? "HEALTH: ONLINE" : "HEALTH: OFFLINE";

    // SPEC-035: Safety Status Update (Brake)
    const safetyBadge = document.getElementById('safety-status');
    if (safetyBadge) {
        const brake = data.main.brake;
        if (brake === "ON") {
            safetyBadge.innerText = "ENGAGED";
            safetyBadge.className = "badge bg-danger";
        } else {
            safetyBadge.innerText = "CLEAR";
            safetyBadge.className = "badge bg-success";
        }
    }

    const gate = data.gateway;
    if (gate) {
        const gateBadge = document.getElementById('conn-gate');
        gateBadge.className = gate.online ? "badge bg-success me-2" : "badge bg-danger me-2";
        gateBadge.innerText = gate.online ? "GATEWAY: ONLINE" : "GATEWAY: OFFLINE";
    }

    // Community tab — metric cards (SPEC-030)
    const cTemp = document.getElementById('c-temp');
    const cSalinity = document.getElementById('c-salinity');
    const cDo = document.getElementById('c-do');
    const cStatus = document.getElementById('c-status');
    if (cTemp) cTemp.innerText = data.main.water_temp != null ? data.main.water_temp + ' °C' : '--';
    if (cSalinity) {
        if (data.main.ec != null) {
            // Rough EC (μS/cm) → PSU conversion; precise mapping needs PSS-78 at temp.
            const psu = (parseFloat(data.main.ec) * 0.00055).toFixed(2);
            cSalinity.innerText = psu;
        } else {
            cSalinity.innerText = '--';
        }
    }
    if (cDo) cDo.innerText = data.main.do != null ? data.main.do : '--';
    if (cStatus) {
        const anyOnline = data.main.online || data.health.online;
        cStatus.innerHTML = anyOnline ? '<i class="bi bi-check-circle text-success"></i>' : '<i class="bi bi-x-circle text-danger"></i>';
    }

    // SPEC-026: LoRa Shell Log reassembly
    updateShellLog(data);
}

function updateLoraConfig() {
    const preset = document.getElementById('lora-preset').value;
    const customDiv = document.getElementById('custom-lora-config');
    
    if (preset === "CUSTOM") {
        customDiv.classList.remove('d-none');
    } else {
        customDiv.classList.add('d-none');
        logEvent("Updating LoRa Preset to: " + preset);
        
        fetch('/api/lora/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preset: preset })
        })
        .then(res => res.json())
        .then(data => logEvent("LORA: " + data.message))
        .catch(err => logEvent("LORA ERROR: " + err));
    }
}

function applyCustomConfig() {
    const freq = document.getElementById('lora-freq').value;
    const sf = document.getElementById('lora-sf').value;
    logEvent(`Applying Custom LoRa: Freq=${freq}MHz, SF=${sf}`);
    
    fetch('/api/lora/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset: 'CUSTOM', freq: freq, sf: sf })
    })
    .then(res => res.json())
    .then(data => logEvent("LORA CUSTOM: " + data.message))
    .catch(err => logEvent("LORA ERROR: " + err));
}

function runLoraTest(mode) {
    logEvent("Starting LoRa Test: " + mode);
    
    const progressDiv = document.getElementById('stress-progress');
    const pb = document.getElementById('pb-stress');
    const countText = document.getElementById('stress-count');
    const resultDiv = document.getElementById('stress-result');
    const pdrValue = document.getElementById('val-pdr');

    if (mode === 'STRESS') {
        progressDiv.classList.remove('d-none');
        resultDiv.classList.add('d-none');
        pb.style.width = "10%";
        pb.className = "progress-bar bg-warning progress-bar-striped progress-bar-animated";
        countText.innerText = "Processing...";
    }

    fetch('/api/lora/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            if (mode === 'PING') {
                if (data.latency) {
                    document.getElementById('val-rtt').innerText = data.latency + " ms";
                    document.getElementById('badge-latency').innerText = "SUCCESS";
                    document.getElementById('badge-latency').className = "badge bg-success mt-2";
                    logEvent(`TEST SUCCESS: RTT=${data.latency}ms, PDR=${data.pdr}%`);
                } else {
                    logEvent("TEST: " + data.message);
                }
            } else if (mode === 'STRESS') {
                pb.style.width = "100%";
                pb.classList.remove('progress-bar-animated');
                pb.className = "progress-bar bg-success";
                countText.innerText = "Complete";
                
                resultDiv.classList.remove('d-none');
                pdrValue.innerText = data.message;
                logEvent(`STRESS TEST: ${data.message}`);
            }
        } else {
            logEvent("TEST ERROR: " + data.message);
            if (mode === 'PING') {
                document.getElementById('badge-latency').innerText = "FAILED";
                document.getElementById('badge-latency').className = "badge bg-danger mt-2";
            } else {
                pb.className = "progress-bar bg-danger";
                countText.innerText = "FAILED";
            }
        }
    })
    .catch(err => {
        logEvent("TEST ERROR: " + err);
        if (mode === 'PING') {
            document.getElementById('badge-latency').innerText = "ERROR";
            document.getElementById('badge-latency').className = "badge bg-danger mt-2";
        } else {
            pb.className = "progress-bar bg-danger";
            countText.innerText = "ERROR";
        }
    });
}

// SPEC-033 — Debug pin toggle (UV)
function debugUv(state) {
    const log = document.getElementById('debug-log');
    if (log) log.textContent = `> UV:${state} ...`;
    authFetch('/api/debug/uv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: state })
    })
    .then(res => res.json().then(data => ({ status: res.status, data })))
    .then(({ status, data }) => {
        const ts = new Date().toISOString().split('T')[1].replace('Z', '');
        if (log) log.textContent = `[${ts}] HTTP ${status}\n${JSON.stringify(data, null, 2)}`;
        logEvent(`DEBUG UV:${state} -> ${data.status || data.message || 'OK'}`);
    })
    .catch(err => {
        if (log) log.textContent = `ERROR: ${err}`;
        logEvent("DEBUG UV ERROR: " + err);
    });
}

function sendCommand(cmd) {
    fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: 'main', cmd: cmd })
    })
    .then(res => res.json())
    .then(data => {
        logEvent("CMD SENT: " + cmd + " -> " + (data.status || "OK"));
    })
    .catch(err => logEvent("CMD ERROR: " + err));
}

function confirmSoftReboot(target) {
    const label = target === 'main' ? 'SYSTEM A (Main)' : 'SYSTEM B (Health)';
    if (confirm(`Soft Reboot ${label}?\n\nThis will gracefully restart the Pi via LoRa. Try this before using Hard Reset.`)) {
        logEvent(`Sending SOFT_REBOOT to ${label} via LoRa...`);
        fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: target, cmd: 'SOFT_REBOOT' })
        })
        .then(res => res.json())
        .then(data => logEvent(`SOFT REBOOT ${target.toUpperCase()}: ${data.message || data.status}`))
        .catch(err => logEvent(`SOFT REBOOT ${target.toUpperCase()} FAILED: Backend unreachable`));
    }
}

function confirmRebootMission() {
    if (confirm("WARNING: Are you sure you want to reboot SYSTEM A (Mission Unit) via System B?")) {
        logEvent("Sending REBOOT command to Health Unit (Target: Mission)...");
        fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: 'health', cmd: 'REBOOT' })
        })
        .then(res => res.json())
        .then(data => logEvent("REBOOT MISSION: " + (data.message || data.status)))
        .catch(err => logEvent("REBOOT MISSION FAILED: Backend unreachable"));
    }
}

function confirmRebootHealth() {
    if (confirm("WARNING: Are you sure you want to reboot SYSTEM B (Health Unit) via System A?")) {
        logEvent("Sending REBOOT command to Main Unit (Target: Health)...");
        fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: 'main', cmd: 'REBOOT' })
        })
        .then(res => res.json())
        .then(data => logEvent("REBOOT HEALTH: " + (data.message || data.status)))
        .catch(err => logEvent("REBOOT HEALTH FAILED: Backend unreachable"));
    }
}

function logEvent(msg) {
    const log = document.getElementById('console-log');
    if (!log) return;
    const time = new Date().toLocaleTimeString();
    log.innerHTML = `> [${time}] ${msg}<br>` + log.innerHTML;
}

// UV CAPTURE
function uvCapture() {
    // Pre-UV safety check
    const violations = checkSafetyThresholds();
    if (violations.length > 0) {
        logEvent("UV BLOCKED: Safety violation — " + violations.join(', '));
        alert("UV CAPTURE BLOCKED\n\nSafety thresholds exceeded:\n" + violations.join('\n') + "\n\nDisable the safety toggles to override.");
        return;
    }

    const btn = document.getElementById('btn-uv-capture');
    const overlay = document.getElementById('uv-progress-overlay');
    const statusText = document.getElementById('uv-progress-text');
    const progressBar = document.getElementById('uv-progress-bar');

    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> UV ON...';
    btn.className = 'btn btn-danger btn-sm fw-bold';
    
    if (overlay) {
        overlay.classList.remove('d-none');
        overlay.classList.add('d-flex');
    }
    
    // Reset all tracks
    if (document.getElementById('uv-p-inverter')) document.getElementById('uv-p-inverter').style.width = '0%';
    if (document.getElementById('uv-p-boot')) document.getElementById('uv-p-boot').style.width = '0%';
    if (document.getElementById('uv-p-flash')) document.getElementById('uv-p-flash').style.width = '0%';

    logEvent("UV CAPTURE: Safety check passed. Triggering UV lamp + camera...");

    // Start polling status
    const pollInterval = setInterval(pollCaptureStatus, 500); // Poll faster for better visuals

    fetch('/api/uv/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duration: 10 })
    })
    .then(res => res.json())
    .then(data => {
        clearInterval(pollInterval);
        if (overlay) {
            overlay.classList.add('d-none');
            overlay.classList.remove('d-flex');
        }

        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-lightning-fill"></i> UV CAPTURE';
        btn.className = 'btn btn-warning btn-sm fw-bold';

        if (data.status === 'success' && data.frame_b64) {
            // ... (rest of image handling unchanged)
            // Show captured frame in the main feed
            const feed = document.getElementById('vision-feed');
            const placeholder = document.getElementById('vision-placeholder');
            feed.src = 'data:image/jpeg;base64,' + data.frame_b64;
            feed.classList.remove('d-none');
            placeholder.classList.add('d-none');

            const timeEl = document.getElementById('snapshot-time');
            timeEl.innerText = new Date(data.timestamp * 1000).toLocaleTimeString();

            // Show in detection frame (right panel)
            const alertImg = document.getElementById('latest-alert-img');
            const alertPlaceholder = document.getElementById('alert-placeholder');
            alertImg.src = 'data:image/jpeg;base64,' + data.frame_b64;
            alertImg.classList.remove('d-none');
            alertPlaceholder.classList.add('d-none');

            // Show analysis results
            const a = data.analysis || {};
            const score = a.score || 0;
            document.getElementById('val-score').innerText = score.toFixed(1);

            // Update alert count
            document.getElementById('alert-count').innerText = (score > 0 ? '!' : '0') + ' ALERTS';

            // Add to detection log
            const log = document.getElementById('vision-log');
            if (log.querySelector('.italic')) log.innerHTML = '';
            const time_str = new Date(data.timestamp * 1000).toLocaleTimeString();
            const item = document.createElement('div');
            const scoreClass = score > 20 ? 'text-danger' : (score > 5 ? 'text-warning' : 'text-success');
            item.className = `list-group-item bg-dark ${scoreClass} border-secondary d-flex justify-content-between align-items-center py-2`;
            item.innerHTML = `
                <span>[${time_str}] UV SCAN — ${a.regions || 0} regions, ${a.coverage_pct || 0}% coverage</span>
                <span class="badge ${score > 20 ? 'bg-danger' : (score > 5 ? 'bg-warning' : 'bg-success')}">SCORE: ${score}</span>
            `;
            log.prepend(item);
            while (log.children.length > 10) log.removeChild(log.lastElementChild);

            logEvent(`UV CAPTURE: Score=${score}, Regions=${a.regions || 0}, Coverage=${a.coverage_pct || 0}%`);
        } else {
            logEvent("UV CAPTURE FAILED: " + (data.message || "Unknown error"));
        }
    })
    .catch(err => {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-lightning-fill"></i> UV CAPTURE';
        btn.className = 'btn btn-warning btn-sm fw-bold';
        logEvent("UV CAPTURE ERROR: " + err);
    });
}

// DETECTION CONFIG
function loadDetectionConfig() {
    authFetch('/api/detection/config')
        .then(r => r.json())
        .then(data => {
            if (data.status !== 'success' || !data.config) return;
            const c = data.config;
            document.getElementById('dt-bright').value = c.brightness_thresh;
            document.getElementById('dt-bright-val').innerText = c.brightness_thresh;
            document.getElementById('dt-sat').value = c.saturation_thresh;
            document.getElementById('dt-sat-val').innerText = c.saturation_thresh;
            document.getElementById('dt-region').value = c.min_region_px;
            document.getElementById('dt-region-val').innerText = c.min_region_px;
            document.getElementById('dt-scale').value = c.score_scale;
            document.getElementById('dt-scale-val').innerText = c.score_scale;
            document.getElementById('dt-warmup').value = c.uv_warmup;
            document.getElementById('dt-warmup-val').innerText = c.uv_warmup;
            document.getElementById('dt-morph').value = c.morph_kernel;
            document.getElementById('dt-samples').value = c.capture_samples;
            
            // Night Hunter keys (SPEC-059)
            if (c.hasOwnProperty('sampler_enabled')) {
                document.getElementById('dt-sampler-enabled').checked = c.sampler_enabled;
                document.getElementById('dt-sampler-start').value = c.sampler_start_hour;
                document.getElementById('dt-sampler-end').value = c.sampler_end_hour;
                document.getElementById('dt-sampler-interval').value = c.sampler_interval_min;
            }

            logEvent('Detection config loaded from vision service');
        })
        .catch(() => {});
}

function applyDetectionConfig() {
    const cfg = {
        brightness_thresh: parseInt(document.getElementById('dt-bright').value),
        saturation_thresh: parseInt(document.getElementById('dt-sat').value),
        min_region_px: parseInt(document.getElementById('dt-region').value),
        score_scale: parseInt(document.getElementById('dt-scale').value),
        uv_warmup: parseFloat(document.getElementById('dt-warmup').value),
        morph_kernel: parseInt(document.getElementById('dt-morph').value),
        capture_samples: parseInt(document.getElementById('dt-samples').value),
        sampler_enabled: document.getElementById('dt-sampler-enabled').checked,
        sampler_start_hour: parseInt(document.getElementById('dt-sampler-start').value),
        sampler_end_hour: parseInt(document.getElementById('dt-sampler-end').value),
        sampler_interval_min: parseInt(document.getElementById('dt-sampler-interval').value)
    };

    const statusEl = document.getElementById('dt-status');
    statusEl.style.display = 'block';
    statusEl.className = 'small mt-2 text-warning';
    statusEl.innerText = 'Applying...';

    authFetch('/api/detection/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg)
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            statusEl.className = 'small mt-2 text-success';
            statusEl.innerText = 'Applied: ' + (data.updated || []).join(', ');
            logEvent('Detection config updated: ' + (data.updated || []).join(', '));
        } else {
            statusEl.className = 'small mt-2 text-danger';
            statusEl.innerText = 'Error: ' + (data.message || 'unknown');
        }
        setTimeout(() => { statusEl.style.display = 'none'; }, 5000);
    })
    .catch(err => {
        statusEl.className = 'small mt-2 text-danger';
        statusEl.innerText = 'Failed: ' + err.message;
    });
}

// SAFETY MONITOR
let lastSafetyState = { dist: null, pir: null, safe: true };

function updateThreshold(type) {
    if (type === 'dist') {
        const v = document.getElementById('thresh-dist').value;
        document.getElementById('thresh-dist-val').innerText = v + ' cm';
    } else if (type === 'hyst') {
        const v = document.getElementById('thresh-hyst').value;
        document.getElementById('thresh-hyst-val').innerText = v + ' cm';
    } else if (type === 'pir') {
        const v = document.getElementById('delay-pir').value;
        document.getElementById('delay-pir-val').innerText = v + ' s';
    }
}

// ============================================================================
// SPEC-035 — Panel ↔ Firmware safety-config sync
// ============================================================================
// On page load, GET /api/safety/config and populate the three controls so the
// UI mirrors what the Mega's EEPROM has.
// On any control change, POST /api/safety/config so the firmware is updated
// in real time. The firmware persists to EEPROM, so settings survive reboots
// and any automatic process (e.g. night-time auto UV cycles) reads consistent
// values from the same source.

function _setSafetySaveStatus(msg, kind) {
    let el = document.getElementById('safety-save-status');
    if (!el) return;
    el.textContent = msg || '';
    el.className = 'text-' + (kind === 'error' ? 'danger' : kind === 'ok' ? 'success' : 'muted') + ' small';
}

function loadSafetyConfigFromFirmware() {
    fetch('/api/safety/config').then(r => r.json()).then(payload => {
        if (payload.status !== 'success' || !payload.config) return;
        const c = payload.config;
        // Map firmware fields → existing UI controls
        const pirCb = document.getElementById('safety-pir-block');
        const distCb = document.getElementById('safety-block-uv');
        const thrSlider = document.getElementById('thresh-dist');
        const thrLabel = document.getElementById('thresh-dist-val');
        const hystSlider = document.getElementById('thresh-hyst');
        const hystLabel = document.getElementById('thresh-hyst-val');
        const pirSlider = document.getElementById('delay-pir');
        const pirLabel = document.getElementById('delay-pir-val');

        if (pirCb && c.heat_armed !== null && c.heat_armed !== undefined) {
            pirCb.checked = !!c.heat_armed;
        }
        if (distCb && c.dist_armed !== null && c.dist_armed !== undefined) {
            distCb.checked = !!c.dist_armed;
        }
        if (thrSlider && c.dist_thr_cm) {
            thrSlider.value = c.dist_thr_cm;
            if (thrLabel) thrLabel.innerText = c.dist_thr_cm + ' cm';
        }
        if (hystSlider && c.dist_hyst_cm) {
            hystSlider.value = c.dist_hyst_cm;
            if (hystLabel) hystLabel.innerText = c.dist_hyst_cm + ' cm';
        }
        if (pirSlider && c.heat_clr_ms) {
            const secs = Math.round(c.heat_clr_ms / 1000);
            pirSlider.value = secs;
            if (pirLabel) pirLabel.innerText = secs + ' s';
        }
        _setSafetySaveStatus('Loaded from firmware', 'ok');
        setTimeout(() => _setSafetySaveStatus(''), 2000);
    }).catch(() => { /* silent — safety config is best-effort */ });
}

function pushSafetyConfigToFirmware(partial) {
    // partial = {heat_armed?, dist_armed?, dist_thr_cm?, dist_hyst_cm?, heat_clr_ms?}
    _setSafetySaveStatus('Saving…');
    authFetch('/api/safety/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(partial)
    }).then(r => {
        if (r.status === 403) throw new Error('Admin login required');
        if (!r.ok && r.status !== 207) throw new Error('HTTP ' + r.status);
        return r.json();
    }).then(data => {
        if (data.errors && data.errors.length > 0) {
            _setSafetySaveStatus('Partial: ' + data.errors[0].error, 'error');
        } else {
            _setSafetySaveStatus('Saved to firmware', 'ok');
            setTimeout(() => _setSafetySaveStatus(''), 1500);
        }
    }).catch(err => {
        _setSafetySaveStatus(err.message, 'error');
    });
}

// Hook up the controls. Called once on DOMContentLoaded.
function wireSafetyControls() {
    const pirCb = document.getElementById('safety-pir-block');
    const distCb = document.getElementById('safety-block-uv');
    const thrSlider = document.getElementById('thresh-dist');
    const hystSlider = document.getElementById('thresh-hyst');
    const pirSlider = document.getElementById('delay-pir');

    if (pirCb) {
        pirCb.addEventListener('change', () => {
            pushSafetyConfigToFirmware({ heat_armed: pirCb.checked });
        });
    }
    if (distCb) {
        distCb.addEventListener('change', () => {
            pushSafetyConfigToFirmware({ dist_armed: distCb.checked });
        });
    }
    if (thrSlider) {
        // Use 'change' (fires on release) — avoid hammering firmware while dragging.
        thrSlider.addEventListener('change', () => {
            pushSafetyConfigToFirmware({ dist_thr_cm: parseInt(thrSlider.value, 10) });
        });
    }
    if (hystSlider) {
        hystSlider.addEventListener('change', () => {
            pushSafetyConfigToFirmware({ dist_hyst_cm: parseInt(hystSlider.value, 10) });
        });
    }
    if (pirSlider) {
        pirSlider.addEventListener('change', () => {
            pushSafetyConfigToFirmware({ heat_clr_ms: parseInt(pirSlider.value, 10) * 1000 });
        });
    }
}

function checkSafetyThresholds() {
    const minDist = parseFloat(document.getElementById('thresh-dist').value);
    const distBlock = document.getElementById('safety-block-uv').checked;
    const pirBlock = document.getElementById('safety-pir-block').checked;

    let violations = [];
    const s = lastSafetyState;

    if (distBlock && s.dist !== null && s.dist < minDist) {
        violations.push(`Distance ${s.dist}cm < ${minDist}cm`);
    }
    if (pirBlock && s.pir === 'MOTION') {
        violations.push('PIR: Motion detected');
    }

    // SPEC-035: Badge update removed here; now handled by updateUI based on BRAKE telemetry.
    return violations;
}

function updateSafetySnapshot() {
    fetch('/api/safety/snapshot?t=' + Date.now())
        .then(res => {
            if (!res.ok) return null;
            return res.json();
        })
        .then(data => {
            if (!data || data.status !== 'success') return;

            // Update camera feed
            const feed = document.getElementById('safety-feed');
            const placeholder = document.getElementById('safety-placeholder');
            if (data.frame_b64) {
                feed.src = 'data:image/jpeg;base64,' + data.frame_b64;
                feed.classList.remove('d-none');
                placeholder.classList.add('d-none');
            }

            // Update sensor values
            const distEl = document.getElementById('val-dist');
            const pirEl = document.getElementById('val-pir');

            if (data.distance_cm !== null) {
                distEl.innerText = data.distance_cm.toFixed(1);
                lastSafetyState.dist = data.distance_cm;
            } else {
                distEl.innerText = '--';
                lastSafetyState.dist = null;
            }

            lastSafetyState.pir = data.pir;
            if (data.pir === 'MOTION') {
                pirEl.innerText = 'MOTION';
                pirEl.className = 'fw-bold text-danger font-monospace mb-0';
            } else if (data.pir === 'CLEAR') {
                pirEl.innerText = 'CLEAR';
                pirEl.className = 'fw-bold text-success font-monospace mb-0';
            } else {
                pirEl.innerText = '--';
                pirEl.className = 'fw-bold text-muted font-monospace mb-0';
            }

            // Color-code distance
            const minDist = parseFloat(document.getElementById('thresh-dist').value);
            if (data.distance_cm !== null && data.distance_cm < minDist) {
                distEl.className = 'fw-bold text-danger font-monospace mb-0';
            } else {
                distEl.className = 'fw-bold text-white font-monospace mb-0';
            }

            checkSafetyThresholds();
        })
        .catch(() => {});
}

// VISION FUNCTIONS
function updateVisionSnapshot() {
    fetch('/api/vision/snapshot?t=' + Date.now())
        .then(res => {
            if (!res.ok) return;
            return res.json();
        })
        .then(data => {
            if (!data || !data.snapshot_b64) return;

            const feed = document.getElementById('vision-feed');
            const placeholder = document.getElementById('vision-placeholder');
            const timeEl = document.getElementById('snapshot-time');

            feed.src = 'data:image/jpeg;base64,' + data.snapshot_b64;
            feed.classList.remove('d-none');
            placeholder.classList.add('d-none');

            if (data.snapshot_time) {
                const t = new Date(data.snapshot_time * 1000).toLocaleTimeString();
                timeEl.innerText = t;
            }
        })
        .catch(() => {});
}

function updateVisionStatus() {
    fetch('/api/vision/status')
        .then(res => {
            if (!res.ok) throw new Error("Vision endpoint not ready");
            return res.json();
        })
        .then(data => {
            const statusBadge = document.getElementById('vision-status');
            if (data.online) {
                statusBadge.innerText = "ONLINE";
                statusBadge.className = "badge bg-success";
            } else {
                statusBadge.innerText = "OFFLINE";
                statusBadge.className = "badge bg-secondary";
            }
            document.getElementById('alert-count').innerText = (data.alert_count || 0) + " ALERTS";
        })
        .catch(err => {
            // Silence error if backend REQ-027 not yet implemented
            const statusBadge = document.getElementById('vision-status');
            if (statusBadge) {
                statusBadge.innerText = "OFFLINE";
                statusBadge.className = "badge bg-secondary";
            }
        });
}

function updateVisionAlerts() {
    fetch('/api/vision/alerts/latest')
        .then(res => {
            if (!res.ok) throw new Error("Vision alerts endpoint not ready");
            return res.json();
        })
        .then(data => {
            if (data && data.timestamp) {
                const img = document.getElementById('latest-alert-img');
                const placeholder = document.getElementById('alert-placeholder');
                const score = document.getElementById('val-score');

                if (data.thumbnail_b64) {
                    img.src = `data:image/jpeg;base64,${data.thumbnail_b64}`;
                    img.classList.remove('d-none');
                    placeholder.classList.add('d-none');
                }

                score.innerText = (data.score || 0.0).toFixed(1);
                
                // Prepend to log if new
                const log = document.getElementById('vision-log');
                const lastId = log.firstElementChild ? log.firstElementChild.getAttribute('data-ts') : null;
                
                if (data.timestamp.toString() !== lastId) {
                    if (log.querySelector('.italic')) log.innerHTML = ''; // Clear "No data" placeholder
                    
                    const time = new Date(data.timestamp * 1000).toLocaleTimeString();
                    const item = document.createElement('div');
                    item.className = "list-group-item bg-dark text-danger border-secondary d-flex justify-content-between align-items-center py-2";
                    item.setAttribute('data-ts', data.timestamp);
                    item.innerHTML = `
                        <span>[${time}] OIL DETECTED</span>
                        <span class="badge bg-danger">SCORE: ${data.score}</span>
                    `;
                    log.prepend(item);
                    
                    // Keep last 10
                    while (log.children.length > 10) {
                        log.removeChild(log.lastElementChild);
                    }
                }
            }
        })
        .catch(err => {
            // Silence error if backend REQ-027 not yet implemented
        });
}

// === COMMUNITY TAB CHARTS (SPEC-030) ===

let communityCharts = {};
let communityHours = 24;
let communityLoaded = false;

let communityMap = null;
let communityMapMarker = null;

const CHART_COLORS = {
    temp: '#00bcd4',
    salinity: '#4caf50',
    do: '#ff9800',
    oil: '#f44336',
    solar: '#ffc107'
};

function createCommunityChart(canvasId, label, color, yUnit, extraOpts) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const opts = {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: label,
                data: [],
                borderColor: color,
                backgroundColor: color + '20',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                pointHitRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 400 },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a1e28',
                    titleColor: '#ccc',
                    bodyColor: '#fff',
                    borderColor: '#333',
                    borderWidth: 1,
                    callbacks: {
                        label: function(ctx) { return ctx.parsed.y + ' ' + yUnit; }
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#666', maxTicksLimit: 8, font: { size: 10 } },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    ticks: { color: '#888', font: { size: 10 }, callback: function(v) { return v + ' ' + yUnit; } },
                    grid: { color: 'rgba(255,255,255,0.08)' }
                }
            }
        }
    };

    // Merge extra options (e.g. threshold annotation for oil)
    if (extraOpts) {
        if (extraOpts.annotation) {
            opts.data.datasets.push(extraOpts.annotation);
        }
    }

    return new Chart(ctx, opts);
}

function initCommunityCharts() {
    if (communityCharts.temp) return; // already initialized
    communityCharts.temp = createCommunityChart('chart-temp', 'Water Temp', CHART_COLORS.temp, '°C');
    communityCharts.salinity = createCommunityChart('chart-salinity', 'Salinity', CHART_COLORS.salinity, 'PSU');
    communityCharts.do = createCommunityChart('chart-do', 'Dissolved O₂', CHART_COLORS.do, '%');
    communityCharts.oil = createCommunityChart('chart-oil', 'Oil Score', CHART_COLORS.oil, '', {
        annotation: {
            label: 'Threshold',
            data: [],
            borderColor: '#f4433666',
            borderWidth: 1,
            borderDash: [6, 4],
            pointRadius: 0,
            fill: false,
            tension: 0
        }
    });
    communityCharts.solar = createCommunityChart('chart-solar', 'Solar Input', CHART_COLORS.solar, 'W');

    // Time window buttons
    document.querySelectorAll('#c-time-window button').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('#c-time-window button').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            communityHours = parseInt(this.dataset.hours);
            loadCommunityData();
        });
    });
}

// Deployment-location map (Leaflet). One-time init; safe to call repeatedly.
// Buoy location: Porto da Baleeira, Sagres — single point inside the harbour basin.
function initCommunityMap() {
    if (communityMap) {
        communityMap.invalidateSize();
        return;
    }
    const el = document.getElementById('c-map');
    if (!el || typeof L === 'undefined') return;

    const buoyLatLng = [37.0083, -8.9276];
    communityMap = L.map(el, {
        center: buoyLatLng,
        zoom: 16,
        scrollWheelZoom: false,
        attributionControl: true
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(communityMap);

    const buoyIcon = L.divIcon({
        className: 'op-buoy-marker',
        html: '<div style="width:18px;height:18px;border-radius:50%;background:#00bcd4;border:3px solid #fff;box-shadow:0 0 12px #00bcd4cc;"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9]
    });
    communityMapMarker = L.marker(buoyLatLng, { icon: buoyIcon }).addTo(communityMap);
    communityMapMarker.bindPopup('<strong>OceanPulse Buoy</strong><br>Porto da Baleeira, Sagres');

    // Tab activations resize the container — make sure Leaflet recomputes.
    setTimeout(() => communityMap.invalidateSize(), 250);
}

function formatChartTime(ts) {
    const d = new Date(ts * 1000);
    if (communityHours <= 6) {
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (communityHours <= 24) {
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else {
        return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' +
               d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
}

function updateChart(chart, labels, data, emptyId) {
    if (!chart) return;
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;

    // Fill threshold line for oil chart
    if (chart.data.datasets.length > 1) {
        chart.data.datasets[1].data = labels.map(() => 30);
    }

    chart.update('none');

    const emptyEl = document.getElementById(emptyId);
    if (emptyEl) {
        if (data.length === 0) {
            emptyEl.classList.remove('d-none');
        } else {
            emptyEl.classList.add('d-none');
        }
    }
}

function loadCommunityData() {
    // Fetch telemetry history for main circuit
    fetch('/api/telemetry/history?hours=' + communityHours + '&target=main')
        .then(r => r.json())
        .then(data => {
            if (data.status !== 'success') return;

            const tempLabels = [], tempData = [];
            const salLabels = [], salData = [];
            const doLabels = [], doData = [];

            // History is sorted DESC, reverse for chronological
            const history = (data.history || []).reverse();

            history.forEach(item => {
                const t = formatChartTime(item.ts);
                const d = item.data || {};

                if (d.water_temp != null) {
                    tempLabels.push(t);
                    tempData.push(parseFloat(d.water_temp));
                }
                if (d.ec != null) {
                    salLabels.push(t);
                    salData.push(parseFloat((parseFloat(d.ec) * 0.00055).toFixed(2)));
                }
                // DO history is stored as do_sat (% saturation) — see app.py persistence path.
                // Live ar/metrics also exposes do_mgL, but historical rows currently only have do_sat.
                const doVal = (d.do_sat != null) ? d.do_sat : d.do;
                if (doVal != null) {
                    doLabels.push(t);
                    doData.push(parseFloat(doVal));
                }
            });

            updateChart(communityCharts.temp, tempLabels, tempData, 'chart-temp-empty');
            updateChart(communityCharts.salinity, salLabels, salData, 'chart-salinity-empty');
            updateChart(communityCharts.do, doLabels, doData, 'chart-do-empty');
        })
        .catch(() => {});

    // Fetch vision history for oil graph
    fetch('/api/vision/history?hours=' + communityHours)
        .then(r => r.json())
        .then(data => {
            if (data.status !== 'success') return;

            const oilLabels = [], oilData = [];
            const history = (data.history || []).reverse();

            history.forEach(item => {
                oilLabels.push(formatChartTime(item.ts));
                oilData.push(item.score != null ? item.score : 0);
            });

            console.log('[Community] Oil history:', oilData.length, 'points, chart exists:', !!communityCharts.oil);
            if (!communityCharts.oil) {
                initCommunityCharts();
            }
            updateChart(communityCharts.oil, oilLabels, oilData, 'chart-oil-empty');
        })
        .catch(err => { console.error('[Community] Oil history fetch error:', err); });

    // Fetch power history for the solar-input chart
    fetch('/api/telemetry/history?hours=' + communityHours + '&target=power')
        .then(r => r.json())
        .then(data => {
            if (data.status !== 'success') return;

            const solarLabels = [], solarData = [];
            const history = (data.history || []).reverse();

            // Power telemetry is persisted as {mppt:{panel_w,...}, shunt:{...}}.
            // Live ar/metrics flattens it to solar_w; check both shapes.
            history.forEach(item => {
                const d = item.data || {};
                const w = (d.mppt && d.mppt.panel_w != null) ? d.mppt.panel_w
                        : (d.solar_w != null ? d.solar_w : null);
                if (w != null) {
                    solarLabels.push(formatChartTime(item.ts));
                    solarData.push(parseFloat(w));
                }
            });

            if (!communityCharts.solar) initCommunityCharts();
            updateChart(communityCharts.solar, solarLabels, solarData, 'chart-solar-empty');

            // Update the "now" badge with the most recent sample
            const nowEl = document.getElementById('c-solar-now');
            if (nowEl) {
                if (solarData.length) {
                    nowEl.textContent = solarData[solarData.length - 1].toFixed(1) + ' W';
                } else {
                    nowEl.textContent = '-- W';
                }
            }
        })
        .catch(() => {});

    // Fetch latest vision alert for contour panel
    loadOilContour();
}

function loadOilContour() {
    fetch('/api/vision/alerts/latest')
        .then(r => {
            if (!r.ok) throw new Error('No alerts');
            return r.json();
        })
        .then(data => {
            if (!data || !data.timestamp) {
                showOilClear();
                return;
            }

            const score = data.score || 0;
            const img = document.getElementById('c-oil-img');
            const placeholder = document.getElementById('c-oil-placeholder');
            const panel = document.getElementById('c-oil-panel');
            const panelHeader = document.getElementById('c-oil-panel-header');
            const card = document.getElementById('c-oil-card');
            const statusEl = document.getElementById('c-oil-status');

            // Update contour image (thumbnail has OpenCV contours drawn on it)
            if (data.thumbnail_b64) {
                img.src = 'data:image/jpeg;base64,' + data.thumbnail_b64;
                img.classList.remove('d-none');
                placeholder.classList.add('d-none');
            }

            // Update numerical data — analysis fields come from alert if available
            const regions = data.regions != null ? data.regions : '--';
            const coverage = data.coverage_pct != null ? data.coverage_pct + '%' : '--';
            const pixels = data.fluor_pixels != null ? data.fluor_pixels.toLocaleString() : '--';
            document.getElementById('c-oil-regions').innerText = regions;
            document.getElementById('c-oil-coverage').innerText = coverage;
            document.getElementById('c-oil-pixels').innerText = pixels;
            const scoreEl = document.getElementById('c-oil-score');
            scoreEl.innerHTML = score > 30
                ? '<span class="text-danger fw-bold">' + score + ' / 100</span>'
                : '<span class="text-success">' + score + ' / 100</span>';
            document.getElementById('c-oil-time').innerText = new Date(data.timestamp * 1000).toLocaleString();

            // Style based on detection
            if (score > 30) {
                panel.style.borderColor = '#f44336';
                panelHeader.style.color = '#f44336';
                panelHeader.innerHTML = '<i class="bi bi-exclamation-triangle-fill"></i> OIL SPILL DETECTION — ALERT';
                card.style.borderColor = '#f44336';
                card.classList.add('oil-detected');
                statusEl.innerHTML = '<i class="bi bi-exclamation-triangle text-danger"></i> <span class="text-danger">DETECTED</span>';
            } else {
                card.classList.remove('oil-detected');
                showOilClearStyle();
            }
        })
        .catch(() => {
            showOilClear();
        });
}

function showOilClear() {
    const img = document.getElementById('c-oil-img');
    const placeholder = document.getElementById('c-oil-placeholder');
    if (img) img.classList.add('d-none');
    if (placeholder) placeholder.classList.remove('d-none');
    showOilClearStyle();
}

function showOilClearStyle() {
    const panel = document.getElementById('c-oil-panel');
    const panelHeader = document.getElementById('c-oil-panel-header');
    const card = document.getElementById('c-oil-card');
    const statusEl = document.getElementById('c-oil-status');
    if (panel) panel.style.borderColor = '#4caf50';
    if (panelHeader) {
        panelHeader.style.color = '#4caf50';
        panelHeader.innerHTML = '<i class="bi bi-shield-check"></i> OIL SPILL DETECTION';
    }
    if (card) card.style.borderColor = '#4caf50';
    if (statusEl) statusEl.innerHTML = '<i class="bi bi-check-circle text-success"></i> <span class="text-success">CLEAR</span>';
}

// Load community data when tab is shown
document.addEventListener('DOMContentLoaded', function() {
    const communityTab = document.getElementById('community-tab');
    if (communityTab) {
        communityTab.addEventListener('shown.bs.tab', function() {
            initCommunityCharts();
            initCommunityMap();
            // Small delay to ensure canvases are rendered before loading data
            setTimeout(loadCommunityData, 100);
            communityLoaded = true;
        });

        // If community tab is already active on page load (e.g. refresh)
        if (communityTab.classList.contains('active')) {
            initCommunityCharts();
            initCommunityMap();
            setTimeout(loadCommunityData, 200);
            communityLoaded = true;
        }
    }
});


// ============================================================================
// Manual tab — admin-gated render of ops/SYSTEM_MANUAL.md
// ============================================================================
//
// Fetches GET /api/manual (admin-only on the backend, see obs_center/app.py).
// Renders markdown client-side with marked.js. Builds a clickable table of
// contents from the H2/H3 headings. Search box filters TOC entries.
// Caches the markdown for the session; Refresh button forces a re-fetch.

let _manualCache = null;
let _manualLoading = false;

function setManualStatus(msg, kind) {
    const el = document.getElementById('manual-status');
    if (!el) return;
    if (!msg) { el.classList.add('d-none'); el.textContent = ''; return; }
    el.classList.remove('d-none');
    el.textContent = msg;
    el.className = 'small px-3 pt-3 ' + (
        kind === 'error' ? 'text-danger' :
        kind === 'ok' ? 'text-success' :
        'text-muted'
    );
}

function slugifyHeading(text) {
    return text.toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .trim()
        .replace(/\s+/g, '-')
        .slice(0, 80) || 'section';
}

function buildManualToc(containerEl, articleEl) {
    if (!containerEl || !articleEl) return;
    containerEl.innerHTML = '';
    const headings = articleEl.querySelectorAll('h2, h3');
    const used = new Set();
    const items = [];
    headings.forEach(h => {
        let id = slugifyHeading(h.textContent);
        let candidate = id, n = 1;
        while (used.has(candidate)) { candidate = id + '-' + (++n); }
        used.add(candidate);
        h.id = candidate;
        items.push({ id: candidate, level: h.tagName, text: h.textContent });
    });
    const ul = document.createElement('ul');
    ul.className = 'list-unstyled mb-0';
    items.forEach(it => {
        const li = document.createElement('li');
        li.className = 'manual-toc-item ' + (it.level === 'H3' ? 'ps-3' : '');
        const a = document.createElement('a');
        a.href = '#' + it.id;
        a.className = (it.level === 'H2' ? 'text-info fw-bold' : 'text-light') + ' text-decoration-none d-block py-1';
        a.textContent = it.text;
        a.dataset.tocText = it.text.toLowerCase();
        a.onclick = (ev) => {
            ev.preventDefault();
            const target = articleEl.querySelector('#' + CSS.escape(it.id));
            if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        };
        li.appendChild(a);
        ul.appendChild(li);
    });
    containerEl.appendChild(ul);
}

function filterManualToc(query) {
    const q = (query || '').trim().toLowerCase();
    const items = document.querySelectorAll('#manual-toc .manual-toc-item');
    items.forEach(li => {
        const a = li.querySelector('a');
        if (!a) return;
        const haystack = a.dataset.tocText || '';
        li.style.display = (!q || haystack.includes(q)) ? '' : 'none';
    });
}

function renderManual(markdownText) {
    const article = document.getElementById('manual-content');
    const toc = document.getElementById('manual-toc');
    if (!article) return;
    if (typeof marked === 'undefined') {
        article.innerHTML = '<div class="text-danger">marked.js failed to load — check your network or CDN.</div>';
        return;
    }
    try {
        marked.setOptions({ headerIds: false, mangle: false });
    } catch (e) { /* older marked: ignore */ }
    article.innerHTML = marked.parse(markdownText);
    buildManualToc(toc, article);
}

function loadManual(forceRefresh) {
    const article = document.getElementById('manual-content');
    if (!article) return;
    if (_manualLoading) return;

    if (!forceRefresh && _manualCache) {
        renderManual(_manualCache);
        setManualStatus('Cached. Click Refresh to re-fetch.', 'ok');
        return;
    }

    _manualLoading = true;
    setManualStatus('Loading manual…');
    article.innerHTML = '<div class="text-muted small">Fetching ops/SYSTEM_MANUAL.md…</div>';
    document.getElementById('manual-toc').innerHTML = '';

    authFetch('/api/manual')
        .then(r => {
            if (r.status === 403) throw new Error('Admin authentication required (HTTP 403). Log in as admin to view the manual.');
            if (r.status === 404) throw new Error('Manual not present on this server. Deploy ops/SYSTEM_MANUAL.md to the lab-center filesystem.');
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.text();
        })
        .then(text => {
            _manualCache = text;
            renderManual(text);
            setManualStatus('Loaded ' + text.length.toLocaleString() + ' bytes', 'ok');
        })
        .catch(err => {
            article.innerHTML = '<div class="text-danger">Failed to load manual: ' + err.message + '</div>';
            setManualStatus(err.message, 'error');
        })
        .finally(() => { _manualLoading = false; });
}

// ============================================================================
// SPEC-036 — Power card update (MPPT + SmartShunt via LoRa P:STATUS)
// ============================================================================
const POWER_CS_PILL_CLASS = {
    0: 'bg-secondary',  // Off
    2: 'bg-danger',     // Fault
    3: 'bg-info',       // Bulk
    4: 'bg-warning text-dark', // Absorption
    5: 'bg-success',    // Float
    6: 'bg-secondary',  // Storage
    7: 'bg-warning text-dark', // Equalize
};

function _fmtNum(v, decimals, unit) {
    if (v === null || v === undefined || Number.isNaN(v)) return '—';
    return Number(v).toFixed(decimals) + (unit || '');
}

function _ageString(ts) {
    if (!ts) return 'never';
    const sec = Math.max(0, Math.floor(Date.now() / 1000 - ts));
    if (sec < 60) return sec + 's ago';
    if (sec < 3600) return Math.floor(sec / 60) + 'm ago';
    return Math.floor(sec / 3600) + 'h ago';
}

function updatePowerCard(power) {
    if (!power) return;
    const mppt = power.mppt || {};
    const shunt = power.shunt || {};
    const d = power.derived || {};

    // Battery row
    const battV = shunt.batt_v;
    const battVEl = document.getElementById('pwr-batt-v');
    if (battVEl) {
        battVEl.innerText = _fmtNum(battV, 2, ' V');
        // Colour by voltage: ≥13.0 green, 12.5–13.0 yellow, <12.5 red
        battVEl.className = (battV == null) ? 'text-muted' :
            (battV >= 13.0 ? 'text-success' :
             battV >= 12.5 ? 'text-warning' : 'text-danger');
    }

    // SOC (from SmartShunt) + voltage-derived sanity check
    const soc = shunt.soc;
    const socEl = document.getElementById('pwr-soc');
    if (socEl) {
        socEl.innerText = (soc == null) ? '—' : _fmtNum(soc, 1, '%');
        socEl.className = (soc == null) ? 'text-muted' :
            (soc >= 80 ? 'text-success' :
             soc >= 50 ? 'text-warning' : 'text-danger');
    }
    const socV = d.soc_from_v;
    const socVEl = document.getElementById('pwr-soc-v');
    if (socVEl) {
        socVEl.innerText = (socV == null) ? '' : ('(volt ~' + Math.round(socV) + '%)');
    }
    // Drift warning row
    const driftRow = document.getElementById('pwr-soc-drift-row');
    const driftVal = document.getElementById('pwr-soc-drift-val');
    if (driftRow && driftVal) {
        if (d.soc_synced === false && d.soc_divergence != null) {
            driftVal.innerText = d.soc_divergence;
            driftRow.classList.remove('d-none');
        } else {
            driftRow.classList.add('d-none');
        }
    }

    // Battery net current (signed)
    const battI = shunt.batt_i;
    document.getElementById('pwr-batt-i').innerText =
        (battI == null) ? '—' :
        ((battI >= 0 ? '+' : '') + _fmtNum(battI, 2, ' A'));
    document.getElementById('pwr-batt-i').className =
        (battI == null) ? 'text-muted font-monospace' :
        (battI >= 0 ? 'text-success font-monospace' : 'text-warning font-monospace');

    const battP = shunt.batt_p;
    document.getElementById('pwr-batt-p').innerText =
        (battP == null) ? '—' :
        ((battP >= 0 ? '+' : '') + battP + ' W');

    // Solar
    document.getElementById('pwr-panel-v').innerText = _fmtNum(mppt.panel_v, 1, ' V');
    document.getElementById('pwr-panel-w').innerText =
        (mppt.panel_w == null) ? '—' : (mppt.panel_w + ' W');

    // Charge current (into battery via MPPT)
    document.getElementById('pwr-charge-i').innerText = _fmtNum(mppt.charge_i, 2, ' A');

    // Load output current (MPPT LOAD terminal)
    document.getElementById('pwr-load-i').innerText = _fmtNum(mppt.load_i, 2, ' A');

    // Direct loads (only meaningful when battery is discharging)
    const direct = d.direct_loads_w;
    document.getElementById('pwr-direct-w').innerText =
        (direct == null) ? '—' :
        (direct === 0 ? '0 W' : direct + ' W');

    // Charge state pill
    const csEl = document.getElementById('power-cs-pill');
    if (csEl) {
        if (mppt.cs_name) {
            csEl.innerText = mppt.cs_name;
            csEl.className = 'badge ' + (POWER_CS_PILL_CLASS[mppt.cs] || 'bg-secondary');
        } else {
            csEl.innerText = power.online ? '—' : 'OFFLINE';
            csEl.className = 'badge bg-secondary';
        }
    }

    // MPPT error banner
    const errRow = document.getElementById('pwr-err-row');
    const errText = document.getElementById('pwr-err-text');
    if (errRow && errText) {
        if (mppt.err && mppt.err !== 0) {
            errText.innerText = 'MPPT error code ' + mppt.err;
            errRow.classList.remove('d-none');
        } else {
            errRow.classList.add('d-none');
        }
    }

    // Last-update timestamp — prefer server-computed age_s to avoid browser clock drift
    const lu = document.getElementById('pwr-last-update');
    if (lu) {
        if (typeof power.age_s === 'number') {
            lu.innerText = _fmtAgeShort(power.age_s) + ' ago';
        } else {
            lu.innerText = _ageString(power.last_update);
        }
    }

    // Card border colour mirrors online state
    const card = document.getElementById('power-card');
    if (card) {
        card.classList.toggle('border-success', !!power.online);
        card.classList.toggle('border-danger', !power.online);
    }
}


// ============================================================================
// Heartbeat strip — per-LoRa-source inter-arrival latency sparkline (Option A)
// ============================================================================
let _hbInterval = null;

function _drawHeartbeat(canvasId, latencies, expectedSec) {
    const cv = document.getElementById(canvasId);
    if (!cv) return;
    const ctx = cv.getContext('2d');
    // Set CSS-relative pixel dim (canvas attr is height=42 in HTML; widen to actual width).
    const w = cv.clientWidth || cv.width;
    const h = cv.height;
    if (cv.width !== w) cv.width = w;
    ctx.clearRect(0, 0, w, h);

    // baseline (expected cadence)
    const yMax = Math.max(expectedSec * 3, 90);  // ceiling: 3x expected or 90s
    const yScale = (h - 4) / yMax;
    const baselineY = h - 2 - expectedSec * yScale;

    // baseline line (expected cadence reference)
    ctx.strokeStyle = '#283038';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, baselineY);
    ctx.lineTo(w, baselineY);
    ctx.stroke();

    if (!latencies || latencies.length === 0) {
        ctx.fillStyle = '#666';
        ctx.font = '11px monospace';
        ctx.fillText('no data yet', 6, h / 2 + 3);
        return;
    }

    // Plot latencies left-aligned (oldest left, newest right).
    const n = latencies.length;
    const step = w / Math.max(n, 30);
    ctx.strokeStyle = '#4dd0e1';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
        const x = i * step;
        const y = Math.max(2, h - 2 - Math.min(latencies[i], yMax) * yScale);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Plot dots; colour by latency band
    for (let i = 0; i < n; i++) {
        const x = i * step;
        const y = Math.max(2, h - 2 - Math.min(latencies[i], yMax) * yScale);
        const ok = latencies[i] <= expectedSec * 1.5;
        const mid = latencies[i] <= expectedSec * 2.5;
        ctx.fillStyle = ok ? '#69f0ae' : (mid ? '#ffd54f' : '#ff8a65');
        ctx.beginPath();
        ctx.arc(x, y, 2.2, 0, Math.PI * 2);
        ctx.fill();
    }
}

function _fmtAgeShort(sec) {
    if (sec === null || sec === undefined) return '—';
    sec = Math.max(0, Math.floor(sec));
    if (sec < 60) return sec + 's';
    if (sec < 3600) return Math.floor(sec / 60) + 'm' + (sec % 60).toString().padStart(2, '0') + 's';
    return Math.floor(sec / 3600) + 'h' + Math.floor((sec % 3600) / 60) + 'm';
}

function updateHeartbeatStrip() {
    fetch('/api/heartbeat').then(r => r.json()).then(data => {
        const srcs = data.sources || {};
        for (const src of ['main', 'health']) {
            const s = srcs[src] || {};
            const lats = s.latencies_s || [];
            const avg = lats.length ? lats.reduce((a, b) => a + b, 0) / lats.length : null;
            const ageEl = document.getElementById('hb-' + src + '-age');
            const avgEl = document.getElementById('hb-' + src + '-avg');
            if (ageEl) {
                ageEl.innerText = _fmtAgeShort(s.last_age_s);
                ageEl.className = (s.last_age_s == null || s.last_age_s > 90) ? 'text-danger' :
                                  (s.last_age_s > 60) ? 'text-warning' : 'text-success';
            }
            if (avgEl) avgEl.innerText = (avg == null) ? '—' : avg.toFixed(1) + 's';
            // expected cadence: Main 30s, Health 30s (both H+P fold into one feed)
            _drawHeartbeat('hb-' + src + '-canvas', lats, 30);
        }
    }).catch(() => { /* swallow — strip is best-effort */ });
}


// ============================================================================
// Power History tab — Chart.js multi-metric historical view
// ============================================================================
const _pCharts = {};

function _initPowerChart(canvasId, opts) {
    const cv = document.getElementById(canvasId);
    if (!cv) return null;
    if (_pCharts[canvasId]) {
        _pCharts[canvasId].destroy();
    }
    const ctx = cv.getContext('2d');
    _pCharts[canvasId] = new Chart(ctx, opts);
    return _pCharts[canvasId];
}

function _lineDataset(label, color, data, opts) {
    opts = opts || {};
    return Object.assign({
        label: label,
        data: data,
        borderColor: color,
        backgroundColor: color + '22',
        borderWidth: 1.4,
        pointRadius: 0,
        tension: 0.18,
        fill: false,
    }, opts);
}

function _commonLineOpts(yLabel, extras) {
    extras = extras || {};
    return Object.assign({
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
            x: { type: 'time', time: { tooltipFormat: 'HH:mm' },
                 ticks: { color: '#9aa5b1', font: { size: 10 } },
                 grid: { color: '#1f2a33' } },
            y: { title: { display: !!yLabel, text: yLabel, color: '#9aa5b1' },
                 ticks: { color: '#9aa5b1', font: { size: 10 } },
                 grid: { color: '#1f2a33' } },
        },
        plugins: {
            legend: { labels: { color: '#cfd8dc', font: { size: 10 } }, position: 'top' },
            tooltip: { mode: 'index', intersect: false },
            // Chart.js built-in LTTB decimation — keeps the visual shape but caps point count.
            // Without this, 72h/7d/30d ranges (5k-50k samples per chart x 8 charts) freeze the tab.
            decimation: { enabled: true, algorithm: 'lttb', samples: 500 },
        },
        parsing: false,  // required for decimation to kick in with {x,y} datasets
    }, extras);
}

function _pickPath(obj, path) {
    let cur = obj;
    for (const k of path) {
        if (cur == null) return null;
        cur = cur[k];
    }
    return cur == null ? null : cur;
}

function loadPowerHistory() {
    const hours = parseInt(document.getElementById('power-range').value || '6');
    const statusEl = document.getElementById('power-status');
    const summaryEl = document.getElementById('power-summary');
    if (statusEl) statusEl.innerText = 'Loading ' + hours + 'h of power telemetry…';

    fetch('/api/telemetry/history?target=power&hours=' + hours)
        .then(r => r.json())
        .then(payload => {
            if (payload.status !== 'success') throw new Error(payload.message || 'API error');
            const rows = payload.history || [];
            if (rows.length === 0) {
                if (statusEl) statusEl.innerText = 'No power telemetry in this range.';
                return;
            }
            // Rows come back DESC; reverse to ASC for time-series plotting.
            rows.reverse();
            // x must be a numeric ms timestamp (not a Date) for the LTTB decimation plugin
            // to work with parsing:false on the time scale.
            const t  = rows.map(r => r.ts * 1000);
            const xy = (path) => rows.map((r, i) => ({ x: t[i], y: _pickPath(r.data, path) }))
                                     .filter(p => p.y !== null && p.y !== undefined);

            // Battery V (single line)
            _initPowerChart('pchart-battv', {
                type: 'line',
                data: { datasets: [_lineDataset('Battery V (Shunt)', '#69f0ae', xy(['shunt', 'batt_v']))] },
                options: _commonLineOpts('V'),
            });
            // SOC
            _initPowerChart('pchart-soc', {
                type: 'line',
                data: { datasets: [_lineDataset('SOC %', '#4dd0e1', xy(['shunt', 'soc']))] },
                options: _commonLineOpts('%', { scales: { y: { min: 0, max: 100, ticks: { color: '#9aa5b1' }, grid: { color: '#1f2a33' } }, x: { type: 'time', ticks: { color: '#9aa5b1' }, grid: { color: '#1f2a33' } } } }),
            });
            // Solar V & W (two y-axes — but Chart.js multi-axis adds noise; combine on one)
            _initPowerChart('pchart-solar', {
                type: 'line',
                data: {
                    datasets: [
                        _lineDataset('Panel V', '#82b1ff', xy(['mppt', 'panel_v'])),
                        _lineDataset('Panel W', '#ffd54f', xy(['mppt', 'panel_w'])),
                    ]
                },
                options: _commonLineOpts(''),
            });
            // Battery current (signed)
            _initPowerChart('pchart-batti', {
                type: 'line',
                data: { datasets: [_lineDataset('Battery I (Shunt)', '#ff8a65', xy(['shunt', 'batt_i']))] },
                options: _commonLineOpts('A'),
            });
            // Battery power (signed)
            _initPowerChart('pchart-battp', {
                type: 'line',
                data: { datasets: [_lineDataset('Battery W (Shunt)', '#ce93d8', xy(['shunt', 'batt_p']))] },
                options: _commonLineOpts('W'),
            });
            // MPPT currents
            _initPowerChart('pchart-mppti', {
                type: 'line',
                data: {
                    datasets: [
                        _lineDataset('Charge I', '#69f0ae', xy(['mppt', 'charge_i'])),
                        _lineDataset('LOAD I',  '#ffd54f', xy(['mppt', 'load_i'])),
                    ]
                },
                options: _commonLineOpts('A'),
            });
            // Charge state — step plot (0..7)
            _initPowerChart('pchart-cs', {
                type: 'line',
                data: { datasets: [_lineDataset('CS', '#4dd0e1', xy(['mppt', 'cs']), { stepped: true, pointRadius: 0 })] },
                options: _commonLineOpts('CS', { scales: {
                    x: { type: 'time', ticks: { color: '#9aa5b1' }, grid: { color: '#1f2a33' } },
                    y: { min: 0, max: 7, ticks: { color: '#9aa5b1', stepSize: 1, callback: v => ({0:'Off',2:'Fault',3:'Bulk',4:'Abs',5:'Float',6:'Storage',7:'Equalize'}[v] || v) }, grid: { color: '#1f2a33' } }
                }}),
            });
            // Errors + direct loads (combined sparkline)
            _initPowerChart('pchart-misc', {
                type: 'line',
                data: {
                    datasets: [
                        _lineDataset('MPPT ERR', '#ff8a65', xy(['mppt', 'err']), { borderWidth: 1.8 }),
                    ]
                },
                options: _commonLineOpts('ERR code'),
            });

            const tFirst = rows[0].ts, tLast = rows[rows.length - 1].ts;
            const spanH = ((tLast - tFirst) / 3600).toFixed(1);
            if (statusEl) statusEl.innerText = '';
            if (summaryEl) summaryEl.innerText = `Loaded ${rows.length} samples spanning ${spanH} h (${new Date(tFirst*1000).toLocaleString()} → ${new Date(tLast*1000).toLocaleString()})`;
        })
        .catch(err => {
            if (statusEl) statusEl.innerText = 'Failed to load: ' + err.message;
        });
}


document.addEventListener('DOMContentLoaded', function () {
    // SPEC-035: pull current firmware safety config into the UI, then wire the
    // controls so any change pushes back to firmware in real time.
    setTimeout(() => {
        loadSafetyConfigFromFirmware();
        wireSafetyControls();
    }, 800);  // small delay so admin-only controls are visible (if logged in)

    // Heartbeat strip: start polling every 3 s while page is open.
    setInterval(updateHeartbeatStrip, 3000);
    updateHeartbeatStrip();

    // Power tab lazy-load on activation + Refresh button + range change
    const ptab = document.getElementById('power-tab');
    if (ptab) {
        ptab.addEventListener('shown.bs.tab', () => loadPowerHistory());
        if (ptab.classList.contains('active')) loadPowerHistory();
    }
    const prange = document.getElementById('power-range');
    if (prange) prange.addEventListener('change', () => loadPowerHistory());

    const tabBtn = document.getElementById('manual-tab');
    if (tabBtn) {
        tabBtn.addEventListener('shown.bs.tab', () => loadManual(false));
        if (tabBtn.classList.contains('active')) {
            loadManual(false);
        }
    }
    const search = document.getElementById('manual-search');
    if (search) {
        search.addEventListener('input', (e) => filterManualToc(e.target.value));
    }
});

// ============================================================================
// SPEC-026 — LoRa Remote Shell (Emergency Recovery)
// ============================================================================

function executeShell() {
    const target = document.getElementById('shell-target').value;
    const cmd = document.getElementById('shell-cmd').value.trim();
    const logEl = document.getElementById('shell-log');
    const btn = document.getElementById('btn-shell-exec');

    if (!cmd) return;

    btn.disabled = true;
    logEl.innerText += `\n[${new Date().toLocaleTimeString()}] Executing on ${target}: ${cmd}...\n`;
    logEl.scrollTop = logEl.scrollHeight;

    authFetch('/api/shell/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target, cmd })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            logEl.innerText += `[${new Date().toLocaleTimeString()}] ${data.message}\n`;
        } else {
            logEl.innerText += `[${new Date().toLocaleTimeString()}] ERROR: ${data.message}\n`;
            btn.disabled = false;
        }
        logEl.scrollTop = logEl.scrollHeight;
    })
    .catch(err => {
        logEl.innerText += `[${new Date().toLocaleTimeString()}] FETCH ERROR: ${err.message}\n`;
        btn.disabled = false;
        logEl.scrollTop = logEl.scrollHeight;
    });
}

let lastShellAckId = { main: null, health: null };

function updateShellLog(data) {
    const logEl = document.getElementById('shell-log');
    if (!logEl) return;

    ['main', 'health'].forEach(target => {
        const ack = data[target].shell_ack;
        if (ack && ack.cmd_id !== lastShellAckId[target]) {
            lastShellAckId[target] = ack.cmd_id;
            const btn = document.getElementById('btn-shell-exec');
            if (btn) btn.disabled = false;

            logEl.innerText += `\n[${new Date().toLocaleTimeString()}] RESPONSE from ${target} (ID: ${ack.cmd_id}):\n${ack.output}\n`;
            logEl.scrollTop = logEl.scrollHeight;
        }
    });
}

// ============================================================
// SPEC-034 — EC calibration tab handlers
// ============================================================

function _calLog(line, cls) {
    const el = document.getElementById('cal-ec-console');
    if (!el) return;
    const ts = new Date().toLocaleTimeString();
    const div = document.createElement('div');
    div.className = cls || 'text-success';
    div.innerHTML = `<span class="text-muted">${ts}</span> ${line}`;
    el.appendChild(div);
    el.scrollTop = el.scrollHeight;
}

function _calEscapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function ecCalSend(atlasCmd, timeoutMs, btn) {
    if (!atlasCmd) return;
    if (btn) { btn.disabled = true; btn._origText = btn._origText || btn.innerHTML; btn.innerHTML = 'sending…'; }
    _calLog(`&gt; <span class="text-info">EC:CMD:${_calEscapeHtml(atlasCmd)}:${timeoutMs}</span>`);
    fetch('/api/cal/ec', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: atlasCmd, timeout_ms: timeoutMs })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            _calLog(`&lt; <span class="text-success">${_calEscapeHtml(data.atlas_reply || '(empty)')}</span>`);
            if (data.atlas_status) _calLog(`  status: <span class="text-muted">${_calEscapeHtml(data.atlas_status)}</span>`, 'text-muted');
            const lc = atlasCmd.toLowerCase();
            if (lc.startsWith('cal')) ecCalRefreshStatus();
        } else {
            _calLog(`! <span class="text-danger">ERROR: ${_calEscapeHtml(data.message || JSON.stringify(data))}</span>`, 'text-danger');
        }
    })
    .catch(err => _calLog(`! <span class="text-danger">network: ${_calEscapeHtml(String(err))}</span>`, 'text-danger'))
    .finally(() => { if (btn) { btn.disabled = false; btn.innerHTML = btn._origText || btn.innerHTML; } });
}

function ecCalReadLive() {
    _calLog(`&gt; <span class="text-info">EC:READ</span> (live R)`);
    fetch('/api/cal/ec', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: 'R', timeout_ms: 1200 })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            const reply = (data.atlas_reply || '').trim();
            _calLog(`&lt; <span class="text-success">${_calEscapeHtml(reply || '(empty)')}</span>`);
            const parts = reply.split(',').map(s => s.trim()).filter(s => s);
            if (parts.length >= 1) document.getElementById('cal-ec-live').innerText = parts[0];
            if (parts.length >= 2) document.getElementById('cal-sal-live').innerText = parts[parts.length - 1];
        } else {
            _calLog(`! <span class="text-danger">${_calEscapeHtml(data.message || 'error')}</span>`, 'text-danger');
        }
    })
    .catch(err => _calLog(`! <span class="text-danger">${_calEscapeHtml(String(err))}</span>`, 'text-danger'));
}

function ecCalRefreshStatus() {
    fetch('/api/cal/ec', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: 'Cal,?', timeout_ms: 600 })
    })
    .then(r => r.json())
    .then(data => {
        const pill = document.getElementById('cal-ec-status');
        if (!pill) return;
        if (data.status === 'success' && data.atlas_reply) {
            const m = data.atlas_reply.match(/\?CAL,(\d)/i);
            if (m) {
                const n = parseInt(m[1], 10);
                pill.innerText = `CAL: ${n}-point`;
                pill.className = 'badge ' + (n >= 2 ? 'bg-success' : n === 1 ? 'bg-warning text-dark' : 'bg-danger');
            } else {
                pill.innerText = 'CAL: ?';
                pill.className = 'badge bg-secondary';
            }
        }
    })
    .catch(() => {});
}

function ecCalConfirmClear(btn) {
    if (!confirm('Clear ALL EC calibration data? The probe reverts to factory defaults and needs re-calibration. Continue?')) return;
    ecCalSend('Cal,clear', 1500, btn);
}

// ============================================================
// SPEC-034 — DO calibration handlers (DFRobot optical, Modbus)
// ============================================================

function _doLog(line, cls) {
    const el = document.getElementById('cal-do-console');
    if (!el) return;
    const ts = new Date().toLocaleTimeString();
    const div = document.createElement('div');
    div.className = cls || 'text-success';
    div.innerHTML = `<span class="text-muted">${ts}</span> ${line}`;
    el.appendChild(div);
    el.scrollTop = el.scrollHeight;
}

function doCalSend(cmd, btn, opts) {
    opts = opts || {};
    if (btn) { btn.disabled = true; btn._origText = btn._origText || btn.innerHTML; btn.innerHTML = 'sending…'; }
    _doLog(`&gt; <span class="text-info">${_calEscapeHtml(cmd)}</span>`);
    fetch('/api/cal/do', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            _doLog(`&lt; <span class="text-success">${_calEscapeHtml(JSON.stringify(data))}</span>`);
            // Update live readout if DO:READ
            if (cmd === 'DO:READ' && data.data) {
                document.getElementById('cal-do-sat').innerText = data.data.do_sat;
                document.getElementById('cal-do-mgL').innerText = data.data.do_mgL;
                document.getElementById('cal-do-wtemp').innerText = data.data.water_temp;
                const pill = document.getElementById('cal-do-status');
                if (pill) { pill.innerText = `${data.data.do_sat}% sat`; pill.className = 'badge bg-info text-dark'; }
            }
            // If opts.into specified, drop the named field into the input box
            if (opts.into && opts.field && data[opts.field] != null) {
                const el = document.getElementById(opts.into);
                if (el) el.value = data[opts.field];
            }
            // After a calibration write, auto-refresh the live reading
            if (cmd.startsWith('DO:CAL:')) {
                setTimeout(() => doCalSend('DO:READ', null), 1500);
            }
        } else {
            _doLog(`! <span class="text-danger">ERROR: ${_calEscapeHtml(data.message || JSON.stringify(data))}</span>`, 'text-danger');
        }
    })
    .catch(err => _doLog(`! <span class="text-danger">network: ${_calEscapeHtml(String(err))}</span>`, 'text-danger'))
    .finally(() => { if (btn) { btn.disabled = false; btn.innerHTML = btn._origText || btn.innerHTML; } });
}

document.addEventListener('DOMContentLoaded', () => {
    const calTabBtn = document.getElementById('cal-tab');
    if (calTabBtn) {
        calTabBtn.addEventListener('shown.bs.tab', () => {
            ecCalRefreshStatus();
            ecCalReadLive();
            doCalSend('DO:READ', null);
            doCalSend('DO:SAL:GET', null, {into:'cal-do-sal-val', field:'salinity_ppt'});
            doCalSend('DO:PRESS:GET', null, {into:'cal-do-press-val', field:'pressure_x100'});
        });
    }

    // GATEWAY TAB (SPEC-060)
    const gwTabBtn = document.getElementById('gateway-tab');
    if (gwTabBtn) {
        gwTabBtn.addEventListener('shown.bs.tab', () => loadGatewayWifiStatus());
    }

    const manualTabBtn = document.getElementById('manual-tab');
    if (manualTabBtn) {
        manualTabBtn.addEventListener('shown.bs.tab', () => loadManual(false));
    }
});

// GATEWAY MANAGEMENT (SPEC-060)
function loadGatewayWifiStatus() {
    fetch('/api/gateway/status')
        .then(r => r.json())
        .then(data => {
            if (data.status !== 'success' || !data.interfaces) return;
            
            const render = (iface, config) => {
                const badge = document.getElementById(`gw-${iface}-badge`);
                const conn = document.getElementById(`gw-${iface}-conn`);
                const ip = document.getElementById(`gw-${iface}-ip`);
                if (!badge || !conn || !ip) return;

                if (config.up) {
                    badge.innerText = 'ONLINE';
                    badge.className = 'badge bg-success';
                } else {
                    badge.innerText = 'OFFLINE';
                    badge.className = 'badge bg-secondary';
                }
                
                conn.innerText = config.connection || 'None';
                ip.innerText = config.ip || '---';
            };
            
            render('wlan0', data.interfaces.wlan0);
            render('wlan1', data.interfaces.wlan1);
        })
        .catch(err => {
            console.error('Failed to load gateway status:', err);
        });
}

function controlGatewayWifi(iface, action) {
    if (!confirm(`Are you sure you want to set ${iface} to ${action}? This might disconnect the gateway.`)) return;

    authFetch('/api/gateway/wifi', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interface: iface, action: action })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            logEvent(`Gateway WiFi: ${iface} set to ${action}`);
            setTimeout(loadGatewayWifiStatus, 2000);
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(err => {
        alert('Network error controlling gateway WiFi');
    });
}

function uvSyncNow() {
    const btn = document.getElementById('btn-uv-sync');
    if (btn) {
        btn.disabled = true;
        btn.classList.replace('btn-outline-warning', 'btn-warning');
        btn.innerHTML = '<i class="bi bi-check-circle-fill"></i> FLASH MARKED!';
    }
    
    fetch('/api/uv/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(res => res.json())
    .then(data => {
        logEvent("UV SYNC: Manual trigger sent. Entering high-speed capture.");
    })
    .catch(err => {
        logEvent("UV SYNC: Failed: " + err);
    });
}

function pollCaptureStatus() {
    fetch('/api/uv/status')
        .then(r => r.json())
        .then(data => {
            const statusText = document.getElementById('uv-progress-text');
            const pInverter = document.getElementById('uv-p-inverter');
            const pBoot = document.getElementById('uv-p-boot');
            const pFlash = document.getElementById('uv-p-flash');
            const btnSync = document.getElementById('btn-uv-sync');
            
            const tInverter = document.getElementById('uv-t-inverter');
            const tBoot = document.getElementById('uv-t-boot');
            const tFlash = document.getElementById('uv-t-flash');

            if (!data.active) {
                if (btnSync) {
                    btnSync.disabled = true;
                    btnSync.classList.replace('btn-warning', 'btn-outline-warning');
                    btnSync.innerHTML = '<i class="bi bi-camera-fill"></i> MARK FLASH / SYNC NOW';
                }
                return;
            }

            // Sync button is live across the WAIT (HARDWARE_DELAY) and the FLASH (BURST).
            // ANALYSIS / IDLE disable it. uvSyncNow() flips it to "MARKED" on press.
            if (btnSync) {
                if (data.stage === 'HARDWARE_DELAY' || data.stage === 'BURST') {
                    if (btnSync.disabled && !btnSync.innerHTML.includes('MARKED')) {
                        btnSync.disabled = false;
                    }
                } else if (data.stage === 'ANALYSIS') {
                    btnSync.disabled = true;
                }
            }

            // Surface the server-recorded press timestamp (delta from start of stage)
            const markInfo = document.getElementById('uv-mark-info');
            if (markInfo) {
                if (data.manual_sync_at) {
                    const m = data.manual_sync_at;
                    markInfo.innerText = `FLASH MARKED at T+${m.delta_s}s of ${m.stage}`;
                    markInfo.classList.remove('d-none');
                } else {
                    markInfo.classList.add('d-none');
                    markInfo.innerText = '';
                }
            }
            
            // Overall Inverter Progress (0-100% across the whole ~20s)
            if (pInverter) pInverter.style.width = data.progress + '%';
            if (tInverter) tInverter.innerText = data.progress > 0 ? 'ACTIVE (12V ON)' : 'OFF';

            if (statusText) {
                let msg = '';
                switch(data.stage) {
                    case 'WARMUP': 
                        msg = 'Activating UV Relay...'; 
                        break;
                    case 'HARDWARE_DELAY': 
                        msg = `Timer Relay Booting (${data.time_left}s)...`; 
                        // Map 0-10s delay to 0-100% on the boot bar
                        if (pBoot) pBoot.style.width = ((10 - (data.time_left - 8)) / 10 * 100) + '%';
                        if (tBoot) tBoot.innerText = 'BOOTING...';
                        break;
                    case 'BURST': 
                        msg = `FLASH! Peak Analysis (${data.time_left}s)...`; 
                        if (pBoot) pBoot.style.width = '100%';
                        if (tBoot) tBoot.innerText = 'COMPLETE';
                        // Map 0-8s burst to 0-100% on the flash bar
                        if (pFlash) pFlash.style.width = ((8 - data.time_left) / 8 * 100) + '%';
                        if (tFlash) tFlash.innerText = 'FIRING / CAPTURING';
                        break;
                    case 'ANALYSIS': 
                        msg = 'Processing Oil Score...'; 
                        if (pFlash) pFlash.style.width = '100%';
                        if (tFlash) tFlash.innerText = 'COMPLETE';
                        break;
                    default: msg = 'Sequence Active...';
                }
                statusText.innerText = msg;
            }
        })
        .catch(() => {});
}


