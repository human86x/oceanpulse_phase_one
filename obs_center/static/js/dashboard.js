// OceanPulse Dashboard Logic

// Initialize Charts
const ctx = document.getElementById('tdsChart').getContext('2d');
const tdsChart = new Chart(ctx, {
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

const loraCtx = document.getElementById('loraChart').getContext('2d');
const loraChart = new Chart(loraCtx, {
    type: 'line',
    data: {
        labels: Array(30).fill(''),
        datasets: [{
            label: 'RSSI',
            data: Array(30).fill(0),
            borderColor: '#0dcaf0',
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.4,
            fill: false
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: { 
                display: true, 
                min: -140, 
                max: -20,
                grid: { color: '#333' },
                ticks: { color: '#0dcaf0' }
            },
            x: { display: false }
        },
        plugins: { legend: { display: false } },
        animation: false
    }
});

// Tab resizing fix
document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tabEl => {
    tabEl.addEventListener('shown.bs.tab', () => {
        tdsChart.resize();
        loraChart.resize();
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

    // Update Main System
    document.getElementById('val-tds').innerText = data.main.tds !== undefined ? data.main.tds : "---";
    document.getElementById('val-ph').innerText = data.main.ph || "---";
    document.getElementById('val-wtemp').innerText = (data.main.water_temp ? data.main.water_temp + " °C" : "--.- °C");
    document.getElementById('val-volt').innerText = (data.main.voltage ? data.main.voltage + " V" : "--.- V");
    
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
        document.getElementById('pb-rssi').style.width = rssiPerc + "%";
        
        const snrPerc = lora.last_snr ? Math.min(100, Math.max(0, (lora.last_snr + 20) * 2.85)) : 0;
        document.getElementById('pb-snr').style.width = snrPerc + "%";
        
        // LQI
        const lqi = (lora.last_rssi && lora.last_snr) ? calculateLQI(lora.last_rssi, lora.last_snr) : 0;
        const lqiBadge = document.getElementById('val-lqi');
        lqiBadge.innerText = lqi + "%";
        lqiBadge.className = lqi > 70 ? "badge bg-success" : (lqi > 40 ? "badge bg-warning" : "badge bg-danger");

        // Update LoRa Chart
        if (lora.last_rssi !== undefined) {
            loraChart.data.datasets[0].data.push(lora.last_rssi);
            loraChart.data.datasets[0].data.shift();
            loraChart.update();
        }
    }

    // Update Chart
    if (data.main.tds !== undefined) {
        tdsChart.data.datasets[0].data.push(data.main.tds);
        tdsChart.data.datasets[0].data.shift();
        tdsChart.update();
    }

    // Update Health System
    document.getElementById('val-temp').innerText = (data.health.temp ? data.health.temp + " °C" : "--.- °C");
    document.getElementById('val-humid').innerText = (data.health.hum ? data.health.hum + " %" : "-- %");
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
    
    if (mode === 'STRESS') {
        const progressDiv = document.getElementById('stress-progress');
        const pb = document.getElementById('pb-stress');
        const countText = document.getElementById('stress-count');
        
        progressDiv.classList.remove('d-none');
        pb.style.width = "0%";
    }

    fetch('/api/lora/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            if (data.latency) {
                document.getElementById('val-rtt').innerText = data.latency + " ms";
                document.getElementById('badge-latency').innerText = "SUCCESS";
                document.getElementById('badge-latency').className = "badge bg-success mt-2";
                logEvent(`TEST SUCCESS: RTT=${data.latency}ms, PDR=${data.pdr}%`);
            } else {
                logEvent("TEST: " + data.message);
            }
        } else {
            logEvent("TEST ERROR: " + data.message);
            document.getElementById('badge-latency').innerText = "FAILED";
            document.getElementById('badge-latency').className = "badge bg-danger mt-2";
        }
    })
    .catch(err => {
        logEvent("TEST ERROR: " + err);
        document.getElementById('badge-latency').innerText = "ERROR";
        document.getElementById('badge-latency').className = "badge bg-danger mt-2";
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

// Start Loop
setInterval(updateTelemetry, 1000);

