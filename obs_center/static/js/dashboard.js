// OceanPulse Dashboard Logic

// Initialize Chart
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
            borderWidth: 1,
            fill: true,
            tension: 0.4
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                grid: { color: '#333' }
            },
            x: { display: false }
        },
        plugins: {
            legend: { display: false }
        },
        animation: false
    }
});

// Telemetry Loop
function updateTelemetry() {
    fetch('/api/telemetry')
        .then(response => response.json())
        .then(data => {
            // Update Main System
            document.getElementById('val-tds').innerText = data.main.tds;
            document.getElementById('val-volt').innerText = data.main.voltage + " V";
            
            const relayBadge = document.getElementById('val-relay');
            relayBadge.innerText = data.main.relay;
            relayBadge.className = data.main.relay === "ON" 
                ? "badge bg-success p-2 shadow-sm" 
                : "badge bg-secondary p-2";

            // Update Chart
            tdsChart.data.datasets[0].data.push(data.main.tds);
            tdsChart.data.datasets[0].data.shift();
            tdsChart.update();

            // Update Health System
            document.getElementById('val-temp').innerText = data.health.temp + " °C";
            document.getElementById('val-uptime').innerText = data.health.uptime;

            logEvent("Telemetry received. TDS: " + data.main.tds);
        })
        .catch(err => console.error("Telemetry Error:", err));
}

// Command Function
function sendCommand(cmd) {
    fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: 'main', cmd: cmd })
    })
    .then(res => res.json())
    .then(data => {
        logEvent("CMD SENT: " + cmd + " -> " + data.status);
    });
}

function logEvent(msg) {
    const log = document.getElementById('console-log');
    const time = new Date().toLocaleTimeString();
    log.innerHTML = `> [${time}] ${msg}<br>` + log.innerHTML;
}

// Start Loop
setInterval(updateTelemetry, 1000);
