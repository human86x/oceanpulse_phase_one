// OceanPulse Dashboard Logic

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Charts
    const tdsEl = document.getElementById('tdsChart');
    if (tdsEl) {
        const ctx = tdsEl.getContext('2d');
        window.tdsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(60).fill(''),
                datasets: [{
                    label: 'TDS (ppm)',
                    data: Array(60).fill(0),
                    borderColor: '#00ff41',
                    backgroundColor: 'rgba(0, 255, 65, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: { color: '#333' },
                        ticks: { color: '#00ff41' }
                    },
                    x: { display: false }
                },
                plugins: {
                    legend: { display: false }
                },
                animation: { duration: 0 }
            }
        });
    }

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
    setInterval(updateVisionAlerts, 10000);
    setInterval(updateVisionSnapshot, 10000);
    updateVisionSnapshot();
});

// VISION STATE

// Tab resizing fix
document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tabEl => {
    tabEl.addEventListener('shown.bs.tab', () => {
        if (window.tdsChart) window.tdsChart.resize();
        if (window.loraChart) window.loraChart.resize();
    });
});

function updateTelemetry() {
    fetch('api.php')
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

    // Update Main System
    document.getElementById('val-tds').innerText = (data.main.tds != null ? data.main.tds : "N/A");
    document.getElementById('val-ph').innerText = (data.main.ph != null ? data.main.ph : "N/A");
    document.getElementById('val-wtemp').innerText = (data.main.temp != null ? data.main.temp + " °C" : "N/A");
    document.getElementById('val-volt').innerText = (data.main.voltage != null ? data.main.voltage + " V" : "N/A");
    
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

    // Update Chart
    if (data.main.tds !== undefined && window.tdsChart) {
        window.tdsChart.data.datasets[0].data.push(data.main.tds);
        window.tdsChart.data.datasets[0].data.shift();
        window.tdsChart.update();
    }

    // Update Health System
    document.getElementById('val-temp').innerText = (data.health.temp != null ? data.health.temp + " °C" : "N/A");
    document.getElementById('val-humid').innerText = (data.health.hum != null ? data.health.hum + " %" : "N/A");
    document.getElementById('val-uptime').innerText = data.health.uptime || "N/A";
    
    // Update Online Indicators
    document.getElementById('conn-main').className = data.main.online ? "badge bg-success" : "badge bg-danger";
    document.getElementById('conn-main').innerText = data.main.online ? "MAIN: ONLINE" : "MAIN: OFFLINE";
    document.getElementById('conn-health').className = data.health.online ? "badge bg-success" : "badge bg-danger";
    document.getElementById('conn-health').innerText = data.health.online ? "HEALTH: ONLINE" : "HEALTH: OFFLINE";

    const gate = data.gateway;
    if (gate) {
        const gateBadge = document.getElementById('conn-gate');
        gateBadge.className = gate.online ? "badge bg-success me-2" : "badge bg-danger me-2";
        gateBadge.innerText = gate.online ? "GATEWAY: ONLINE" : "GATEWAY: OFFLINE";
    }
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

// VISION FUNCTIONS
function updateVisionSnapshot() {
    fetch('/api/vision/snapshot')
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

