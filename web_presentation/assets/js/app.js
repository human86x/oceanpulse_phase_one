const COMPONENT_DETAILS = {
    "Pi5": { title: "Raspberry Pi 5 (Mission)", desc: "Main computer running OpenCV for oil detection.", power: "3.5W - 6W" },
    "Pi3": { title: "Raspberry Pi 3 (Health)", desc: "Low-power watchdog.", power: "1.5W - 2.5W" },
    "Solar": { title: "Solar Array", desc: "2x 60W Panels.", power: "+120W Peak" },
    "Batt": { title: "LiFePO4 Bank", desc: "12V 50Ah.", power: "Store" },
    "UV_LED": { title: "UV Strobe", desc: "Everbeam 50W 365nm.", power: "50W (Pulse)" },
    "LoRaA": { title: "LoRa Link A", desc: "868 MHz Mesh.", power: "0.1W" },
    "RelayA_Contact": { title: "Watchdog Cutoff", desc: "Normally Closed Relay.", power: "N/A" }
};

let DEFAULT_BOM_DATA = [
    { cat: "0. Compute", tier: "basic", item: "Raspberry Pi 5 4GB (Mission - Repurposed)", cost: 0.00, link: "#", source: "Lab Inventory", bought: true },
    { cat: "0. Compute", tier: "basic", item: "Raspberry Pi 3 B+ (Health - Repurposed)", cost: 0.00, link: "#", source: "Lab Inventory", bought: true },
    { cat: "0. Compute", tier: "basic", item: "Raspberry Pi 4 1GB (Lab Hub)", cost: 45.00, link: "https://mauser.pt/095-1631/raspberry-pi-sc0192-microcomputador-raspberry-pi-4-model-b-1gb", source: "Mauser", bought: false },
    { cat: "0. Compute", tier: "basic", item: "JOY-IT Active Cooler (Pi 5)", cost: 6.90, link: "https://mauser.pt/095-4736/joy-it-rb-heatsink5-dissipador-com-ventoinha-para-raspberry-pi-5", source: "Mauser", bought: true },
    { cat: "0. Compute", tier: "advanced", item: "JOY-IT 3.5\" Touchscreen", cost: 22.98, link: "https://mauser.pt/096-7662/joy-it-display-lcd-3-5-480x320-touchscreen-compativel-com-raspberry-pi", source: "Mauser", bought: true },
    { cat: "0. Compute", tier: "basic", item: "Kingston 128GB MicroSD (x2)", cost: 27.10, link: "https://www.amazon.es/s?k=Kingston+128GB+MicroSD", source: "Amazon", bought: false },
    { cat: "0. Compute", tier: "basic", item: "Arduino Mega 2560 R3 (x2)", cost: 40.00, link: "https://mauser.pt/095-7132/joy-it-ard-mega2560r3-p-microcontrolador-compativel-com-arduino-mega-2560r3-c-cristal-de-alta-precisao", source: "Mauser", bought: true },
    
    { cat: "1. Power", tier: "basic", item: "Offgridtec 60W ETFE Panels (x2)", cost: 98.00, link: "https://greenboatsolutions.com/shop/accessories/solar-panels/offgridtec-etfe-al-60w-v2-semi-flexible-18v-solarpanel.html", source: "GreenBoat", bought: true },
    { cat: "1. Power", tier: "basic", item: "Green Cell 50Ah LiFePO4 (ORDER PENDING)", cost: 154.00, link: "https://mauser.pt/115-0057/green-cell-lfpgc12v50ah-bateria-de-lithium-lifepo4-bms-12-8v-640wh-50a", source: "Mauser", bought: false },
    { cat: "1. Power", tier: "basic", item: "Victron MPPT 75/15", cost: 71.70, link: "https://mauser.pt/095-3813/victron-energy-bluesolar-mppt-75-15-scc010015050r-controlador-de-carga-solar-mppt-75v-12-24v-15a", source: "Mauser", bought: true },
    { cat: "1. Power", tier: "basic", item: "USB-TTL PL2303 (VE.Direct)", cost: 1.85, link: "https://mauser.pt/096-7520/conversor-usb-para-serial-ttl-rs232-pl2303", source: "Mauser", bought: false },
    { cat: "1. Power", tier: "basic", item: "JST-PH 4-pin Cable (VE.Direct)", cost: 0.85, link: "https://mauser.pt/035-5318/ficha-raster-signal-2-00mm-ph-4-pinos-femea-com-fios-de-200mm", source: "Mauser", bought: true },
    { cat: "1. Power", tier: "basic", item: "Marine Fuse Block (6-Way)", cost: 15.00, link: "#", source: "Amazon", bought: false },
    { cat: "1. Power", tier: "basic", item: "12V-5V 5A Buck Converters (x2)", cost: 20.00, link: "#", source: "Amazon", bought: false },
    { cat: "1. Power", tier: "basic", item: "Raspberry Pi UPS HAT", cost: 25.00, link: "#", source: "Botnroll", bought: false },
    { cat: "1. Power", tier: "basic", item: "18650 Li-ion 3000mAh", cost: 5.00, link: "#", source: "Mauser", bought: false },

    { cat: "2. Science", tier: "advanced", item: "Atlas Salinity Kit K 1.0", cost: 252.99, link: "https://eu.robotshop.com/products/atlas-scientific-conductivity-sensor-k-10-kit", source: "RobotShop", bought: false },
    { cat: "2. Science", tier: "advanced", item: "Atlas Dissolved Oxygen Kit", cost: 390.45, link: "https://eu.robotshop.com/products/atlas-scientific-dissolved-oxygen-sensor-kit", source: "RobotShop", bought: false },
    { cat: "2. Science", tier: "advanced", item: "Bar30 Depth/Pressure R2", cost: 99.00, link: "https://eu.robotshop.com/products/bar30-high-resolution-300m-depth-pressure-sensor-r2", source: "RobotShop", bought: false },
    { cat: "2. Science", tier: "advanced", item: "Adafruit BNO055 IMU", cost: 35.00, link: "#", source: "Adafruit", bought: false },
    { cat: "2. Science", tier: "basic", item: "BME280 Temp/Hum/Pres (x3)", cost: 15.00, link: "#", source: "Mauser", bought: false },
    { cat: "2. Science", tier: "basic", item: "INA219 Volt/Curr Sensors (x4)", cost: 20.00, link: "#", source: "Amazon", bought: false },
    { cat: "2. Science", tier: "basic", item: "DS18B20 Temp Probe", cost: 5.00, link: "#", source: "Mauser", bought: false },

    { cat: "3. Comms", tier: "basic", item: "LoRa-E5 Mini Modules (x2)", cost: 55.60, link: "https://mauser.pt/096-9675/seeed-placa-de-desenvolvimento-lora-e5-mini-stm32wle5jc-c-banda-de-frequencia-global", source: "Mauser", bought: true },
    { cat: "3. Comms", tier: "basic", item: "RS485 to TTL Modules (x2)", cost: 4.00, link: "#", source: "Mauser", bought: false },
    { cat: "3. Comms", tier: "basic", item: "5V Relay Modules (x2)", cost: 4.00, link: "#", source: "Mauser", bought: false },
    { cat: "3. Comms", tier: "basic", item: "Portable 4G/LTE WiFi Modem (Lab Internet)", cost: 50.00, link: "https://www.amazon.es/s?k=4G+LTE+USB+Modem+WiFi", source: "Amazon", bought: false },

    { cat: "4. Hull", tier: "basic", item: "Weipu SP21 2-Pin Sets (x3)", cost: 45.00, link: "#", source: "Mauser", bought: false },
    { cat: "4. Hull", tier: "basic", item: "Weipu SP13 4-Pin Sets (x4)", cost: 65.00, link: "#", source: "Mauser", bought: false },
    { cat: "4. Hull", tier: "basic", item: "18 AWG Wire (10m R/B)", cost: 15.00, link: "#", source: "Mauser", bought: false },
    { cat: "4. Hull", tier: "basic", item: "22 AWG Signal Cable (20m)", cost: 20.00, link: "#", source: "Mauser", bought: false },
    { cat: "4. Hull", tier: "basic", item: "Cable Glands PG7/PG9 Pack", cost: 10.00, link: "#", source: "Mauser", bought: false },
    { cat: "4. Hull", tier: "basic", item: "Master Toggle Switch 20A", cost: 5.00, link: "#", source: "Mauser", bought: false },
    { cat: "4. Hull", tier: "basic", item: "M3 Brass Standoff Kit", cost: 15.00, link: "#", source: "Mauser", bought: false },
    { cat: "4. Hull", tier: "basic", item: "Acrylic Sheet (Internal & Window)", cost: 20.00, link: "#", source: "Leroy Merlin", bought: false },
    { cat: "4. Hull", tier: "basic", item: "Small IP65 Junction Boxes (x3)", cost: 10.00, link: "#", source: "Mauser", bought: false },

    { cat: "5. Tools", tier: "basic", item: "Solder Wire Lead-free", cost: 10.00, link: "#", source: "Mauser", bought: false },
    { cat: "5. Tools", tier: "basic", item: "Conformal Coating Spray (PCB Shield)", cost: 15.00, link: "https://mauser.pt/catalog/advanced_search_result.php?keywords=verniz+isolante", source: "Mauser", bought: false },
    { cat: "5. Tools", tier: "basic", item: "Flux Pen/Paste", cost: 5.00, link: "#", source: "Mauser", bought: false },
    { cat: "5. Tools", tier: "basic", item: "Brass Sponge / Cleaner", cost: 5.00, link: "#", source: "Mauser", bought: false },
    { cat: "5. Tools", tier: "basic", item: "Silicone Soldering Mat", cost: 10.00, link: "#", source: "Amazon", bought: false },
    { cat: "5. Tools", tier: "basic", item: "Automatic Wire Strippers", cost: 15.00, link: "#", source: "Mauser", bought: false },
    { cat: "5. Tools", tier: "basic", item: "Offset Right-Angle Ratchet (7cm Clearance)", cost: 12.00, link: "#", source: "Local", bought: false },
    { cat: "5. Tools", tier: "basic", item: "Flush Cutters", cost: 8.00, link: "#", source: "Mauser", bought: false },
    { cat: "5. Tools", tier: "basic", item: "Precision Screwdriver Set", cost: 15.00, link: "#", source: "Mauser", bought: false },
    { cat: "5. Tools", tier: "basic", item: "Crimping Tool", cost: 20.00, link: "#", source: "Mauser", bought: false },

    { cat: "6. Oil System", tier: "advanced", item: "CreateStar 50W UV 365nm Lamp", cost: 46.75, link: "https://www.amazon.es/dp/B0DDSTVT7S", source: "Amazon", bought: true },
    { cat: "6. Oil System", tier: "advanced", item: "Green Cell 300W Inverter", cost: 29.95, link: "https://www.amazon.es/dp/B07QCNFWNT", source: "Amazon", bought: true },
    { cat: "6. Oil System", tier: "advanced", item: "Hailege 30A Relay Module", cost: 10.66, link: "https://www.amazon.es/dp/B07QCNFWNT", source: "Amazon", bought: true },
    { cat: "6. Oil System", tier: "advanced", item: "DFRobot IMX378 Camera (190°)", cost: 32.03, link: "https://mauser.pt/095-5262/dfrobot-sen0633-modulo-de-camera-grande-angular-imx378-190-12-3mp-p-raspberry-pi-4b-5-4056x3040-fov190", source: "Mauser", bought: true },
    { cat: "6. Oil System", tier: "advanced", item: "CSI to HDMI Extension Module (SKU B0091)", cost: 13.99, link: "https://www.arducam.com/product/csi-to-hdmi-adapter-set-for-raspberry-pi-cameras-b0091/", source: "Arducam", bought: false },
    { cat: "6. Oil System", tier: "advanced", item: "IP68 Waterproof Camera Case", cost: 15.00, link: "#", source: "Local", bought: false },
    { cat: "6. Oil System", tier: "advanced", item: "DollaTek NE555 Timer Module", cost: 10.16, link: "https://www.amazon.es/DollaTek-Ajustable-Temporizador-Retransmisi%C3%B3n-Interruptor/dp/B07MB8XXCT/", source: "Amazon", bought: true },
    { cat: "6. Oil System", tier: "advanced", item: "5x HC-SR501 PIR Sensors", cost: 12.19, link: "https://www.amazon.es/dp/B07F9LJS72", source: "Amazon", bought: true },
    { cat: "6. Oil System", tier: "advanced", item: "2x JSN-SR04T Ultrasonic Sensor", cost: 13.21, link: "https://www.amazon.es/dp/B0DDKXCCRH", source: "Amazon", bought: true },
    { cat: "6. Oil System", tier: "advanced", item: "Amber Warning Strobe", cost: 15.00, link: "#", source: "Amazon", bought: false },
    { cat: "6. Oil System", tier: "advanced", item: "Black UV-Blocking Acrylic (3mm)", cost: 20.00, link: "#", source: "Local", bought: false },
    { cat: "6. Oil System", tier: "advanced", item: "IP68 Junction Box (Large)", cost: 15.00, link: "#", source: "Local", bought: false }
];

let BOM_DATA = [...DEFAULT_BOM_DATA];
let currentTierFilter = 'all';
let excludedCategories = new Set();

// --- Persistence Layer ---
async function saveState() {
    const saveBtn = document.getElementById('saveBtn');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = "⏳ Saving...";
    saveBtn.disabled = true;

    const data = {
        bom: BOM_DATA,
        excluded: Array.from(excludedCategories)
    };
    
    try {
        const response = await fetch('api.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        console.log('Remote Save:', result.message);
        saveBtn.innerHTML = "✅ Saved Permanently";
        saveBtn.classList.replace('btn-warning', 'btn-success');
        setTimeout(() => { 
            saveBtn.innerHTML = originalText; 
            saveBtn.disabled = false;
            saveBtn.classList.replace('btn-success', 'btn-warning');
        }, 3000);
    } catch (err) {
        console.error('Remote Save Failed:', err);
        saveBtn.innerHTML = "❌ Error Saving";
        saveBtn.disabled = false;
    }
}

async function loadState() {
    try {
        const response = await fetch('api.php');
        const data = await response.json();
        if (data.bom) {
            BOM_DATA = data.bom;
            excludedCategories = new Set(data.excluded || []);
            console.log('Remote configuration loaded.');
            renderBOM();
        }
    } catch (err) {
        console.error('Remote Load Failed:', err);
        renderBOM();
    }
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    loadState(); // This calls renderBOM once data arrives
    updatePowerCalc();
    setupDiagramInteractivity();
});

function renderBOM() {
    const oilTabBody = document.getElementById('oilBOMBody');
    const bomTableBody = document.getElementById('bomTableBody');
    if (!oilTabBody || !bomTableBody) return;

    oilTabBody.innerHTML = '';
    bomTableBody.innerHTML = '';
    
    let grandTotal = 0;
    const categories = [...new Set(BOM_DATA.map(item => item.cat))].sort();

    categories.forEach(cat => {
        const catItems = BOM_DATA.filter(item => item.cat === cat);
        const isCatExcluded = excludedCategories.has(cat);
        
        let catSubtotal = 0;
        let catRowsHtml = '';

        catItems.forEach((obj) => {
            const originalIndex = BOM_DATA.indexOf(obj);
            
            // ADDITIVE LOGIC
            let isItemValidForFilter = false;
            if (currentTierFilter === 'all') isItemValidForFilter = true;
            if (currentTierFilter === 'basic' && obj.tier === 'basic') isItemValidForFilter = true;
            if (currentTierFilter === 'advanced' && (obj.tier === 'basic' || obj.tier === 'advanced')) isItemValidForFilter = true;

            // Price contribution (Only if category is on AND item is basic/advanced AND NOT BOUGHT)
            if (isItemValidForFilter && !isCatExcluded && obj.tier !== 'excluded' && !obj.bought) {
                catSubtotal += obj.cost;
            }

            const displayStyle = isItemValidForFilter ? '' : 'none';
            const rowOpacity = (!isCatExcluded && obj.tier !== 'excluded') ? '1' : '0.4';
            
            const statusBadge = obj.bought 
                ? '<span class="badge bg-success">Bought</span>' 
                : '<span class="badge bg-warning text-dark">Pending</span>';

            catRowsHtml += `
                <tr style="display: ${displayStyle}; opacity: ${rowOpacity}">
                    <td></td>
                    <td>
                        <select class="form-select form-select-sm" onchange="updateItemTier(${originalIndex}, this.value)">
                            <option value="basic" ${obj.tier === 'basic' ? 'selected' : ''}>Basic</option>
                            <option value="advanced" ${obj.tier === 'advanced' ? 'selected' : ''}>Advanced</option>
                            <option value="excluded" ${obj.tier === 'excluded' ? 'selected' : ''}>Excluded</option>
                        </select>
                    </td>
                    <td>${obj.item}</td>
                    <td>€${obj.cost.toFixed(2)}</td>
                    <td>${statusBadge}</td>
                    <td><a href="${obj.link}" target="_blank" class="btn btn-sm btn-outline-primary">${obj.source}</a></td>
                </tr>`;

            if (cat.includes("Oil") && !isCatExcluded && obj.tier !== 'excluded') {
                oilTabBody.innerHTML += `<tr><td>${obj.item}</td><td>€${obj.cost.toFixed(2)}</td><td>${obj.tier.toUpperCase()}</td><td><a href="${obj.link}" target="_blank" class="btn btn-sm btn-outline-primary">${obj.source}</a></td></tr>`;
            }
        });

        const headerHtml = `
            <tr class="table-dark">
                <td colspan="6">
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" style="width: 40px; height: 20px" ${!isCatExcluded ? 'checked' : ''} onchange="toggleCategory('${cat}')">
                        <label class="form-check-label fw-bold ms-2">${cat}</label>
                    </div>
                </td>
            </tr>`;
        
        const footerHtml = `
            <tr class="table-info" style="display: ${catSubtotal > 0 || currentTierFilter === 'all' ? '' : 'none'}">
                <td colspan="3" class="text-end fw-bold">Subtotal for ${cat}:</td>
                <td class="fw-bold">€${catSubtotal.toFixed(2)}</td>
                <td colspan="2"></td>
            </tr>`;
        
        bomTableBody.innerHTML += headerHtml + catRowsHtml + footerHtml;
        grandTotal += catSubtotal;
    });

    document.getElementById('totalAmount').innerText = "€" + grandTotal.toLocaleString('en-EU', { minimumFractionDigits: 2 });
    document.getElementById('totalLabel').innerText = (currentTierFilter === 'advanced') ? "Total (Basic + Advanced):" : (currentTierFilter === 'basic' ? "Total (Basic Only):" : "Total (All Configured):");
}

window.toggleCategory = function(cat) {
    if (excludedCategories.has(cat)) excludedCategories.delete(cat);
    else excludedCategories.add(cat);
    renderBOM();
}

window.updateItemTier = function(index, newTier) {
    BOM_DATA[index].tier = newTier;
    renderBOM();
}

window.filterBOM = function(tier) {
    currentTierFilter = tier;
    document.querySelectorAll('.btn-group .btn').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-' + tier).classList.add('active');
    renderBOM();
}

window.saveBOM = function() {
    saveState();
}

window.resetBOM = function() {
    if(confirm("Reset all manual changes to default?")) {
        localStorage.clear();
        location.reload();
    }
}

// --- Power Simulator Logic ---
window.updatePowerCalc = function() {
    const season = document.getElementById('seasonSelect').value;
    const battAh = parseInt(document.getElementById('battRange').value);
    document.getElementById('battVal').innerText = battAh + " Ah";
    const voltage = 12.8;
    const battWh = battAh * voltage * 0.8; 
    const dailyLoadWh = 156; 
    let solarGenWh = 0;
    if (season === 'winter') solarGenWh = 100 * 2.5 * 0.75; 
    if (season === 'summer') solarGenWh = 100 * 7.0 * 0.75; 
    if (season === 'storm')  solarGenWh = 100 * 0.5 * 0.75; 
    const balance = solarGenWh - dailyLoadWh;
    const autonomyDays = (battWh / dailyLoadWh).toFixed(1);
    const stats = document.getElementById('powerStats');
    stats.innerHTML = `<li class="list-group-item d-flex justify-content-between"><span>Daily Load:</span> <strong>${dailyLoadWh} Wh</strong></li>
        <li class="list-group-item d-flex justify-content-between"><span>Solar Gen:</span> <strong class="${balance >= 0 ? 'text-success' : 'text-danger'}">${Math.round(solarGenWh)} Wh</strong></li>
        <li class="list-group-item d-flex justify-content-between"><span>Balance:</span> <strong class="${balance >= 0 ? 'text-success' : 'text-danger'}">${Math.round(balance)} Wh/day</strong></li>`;
    document.getElementById('autonomyDisplay').innerText = autonomyDays;
}

function setupDiagramInteractivity() {
    setTimeout(() => {
        document.querySelectorAll('.node').forEach(node => {
            node.style.cursor = "pointer";
            node.addEventListener('mouseenter', () => {
                const text = node.textContent.trim();
                let match = null;
                for (const [key, data] of Object.entries(COMPONENT_DETAILS)) {
                    if (text.includes(data.title.split(' ')[0]) || text.includes(key)) { match = data; break; }
                }
                if (match) {
                    document.getElementById('nodeInfo').innerHTML = `<h5>${match.title}</h5><p>${match.desc}</p><hr><small>Power: <strong>${match.power}</strong></small>`;
                }
            });
        });
    }, 1000);
}