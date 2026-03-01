# SPEC-021: Headless Kiosk Display (Lab Center)

**Status:** APPROVED
**Priority:** MEDIUM
**Owner:** Systems_Architect (spec), DevOps_Engineer (implementation)
**Created:** 2026-02-09
**References:** SPEC-001 (Obs Center)

---

## 1. Purpose
Define the architecture for displaying the OceanPulse Observation Center dashboard on a physical screen connected to the `lab-center` Pi (192.168.43.236) without installing a full Desktop Environment.

---

## 2. Technical Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| **Display Server** | Wayland (DRM/KMS) | Native Pi 5/4 support, modern, high performance |
| **Compositor** | **Cage** | Minimalist "kiosk" compositor; only allows one full-screen app |
| **Browser** | **Chromium (Kiosk Mode)** | Wide compatibility with dashboard JS/CSS, supports headless hardware acceleration |
| **Service Manager** | Systemd | Ensures display starts on boot and restarts on failure |

---

## 3. Implementation Plan

### 3.1 Dependencies (to be installed by DevOps)
- `cage`
- `chromium-browser`
- `xwayland` (if needed for older browser versions)
- `seatd` (for unprivileged graphics access)

### 3.2 Kiosk Script
A wrapper script (`ops/launch_kiosk.sh`) will handle browser flags:
```bash
#!/bin/bash
# Chromium Kiosk Flags
FLAGS="--kiosk 
       --no-first-run 
       --noerrdialogs 
       --disable-infobars 
       --autoplay-policy=no-user-gesture-required 
       --check-for-update-interval=31536000"

URL="http://localhost:5000"

# Launch using Cage
exec cage -- chromium-browser $FLAGS $URL
```

### 3.3 Systemd Service (`obs-kiosk.service`)
```ini
[Unit]
Description=OceanPulse Headless Kiosk
After=network.target obs-center.service

[Service]
User=lab
Type=simple
Environment=XDG_RUNTIME_DIR=/run/user/1000
ExecStart=/home/human/Projects/oceanpulse_phase_one/ops/launch_kiosk.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 4. Security & Optimization
- **Auto-Hide Cursor:** Use `--incognito` or a custom CSS `cursor: none` in the dashboard.
- **Hardware Acceleration:** Ensure `libgbm` and `egl` are active.
- **Power Management:** Disable screen blanking/sleeping via kernel parameters or `cage` config.

---

## 5. Success Criteria
- [ ] `lab-center` Pi boots directly into the Observation Center dashboard.
- [ ] No desktop, taskbar, or desktop-level UI elements are visible.
- [ ] Screen automatically recovers (restarts) if the browser crashes.
- [ ] Dashboard is interactive via physical mouse/touchscreen (if connected).
