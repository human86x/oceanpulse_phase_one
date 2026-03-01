# SPEC-001: Observational Center Dashboard

## 1. Overview
The Observational Center (OpsCenter) is a web-based dashboard designed to provide real-time monitoring and control over System A (Main) and System B (Health). It serves as the primary interface for mission operators.

## 2. Technical Stack
- **Backend:** Python (Flask)
- **Frontend:** HTML5, CSS3 (Bootstrap 5), JavaScript (Vanilla or jQuery)
- **Visualization:** Chart.js (for telemetry graphs)
- **Protocol:** HTTP/REST (simulation mode initially)

## 3. Functional Requirements
### 3.1 Telemetry Monitoring
- Display live **TDS (Total Dissolved Solids)** values from System A.
- Display live **Voltage** readings (simulated for now).
- Display **Connection Status** (Online/Offline) for both `main` and `health` units.
- Real-time chart showing the last 60 seconds of TDS data.

### 3.2 Command & Control
- **Relay Toggle:** Button to send `RELAY_ON` / `RELAY_OFF` commands to System A.
- **System Reboot:** UI action to trigger a reboot command (to be implemented via SSH/API).
- **Simulation Toggle:** A switch to toggle between "Live Data" and "Mock Data".

## 4. UI/UX Design (Mission Control Aesthetic)
- **Theme:** Dark Mode (Background: #0b0e14, Text: #00ff41 - Terminal Green).
- **Layout:**
    - **Header:** Project Name "OceanPulse Phase 1" + Global Status Indicators.
    - **Main Area (Grid):**
        - **Card 1: System A (Mission):** Live TDS readout, Graph, Relay Status, "Strobe" Control Button.
        - **Card 2: System B (Health):** Heartbeat monitor, Uptime, Internal Temp (simulated).
    - **Footer:** System Logs / Activity Feed.

## 5. API Endpoints (Backend Implementation)
- `GET /api/telemetry`: Returns current sensor data in JSON format.
- `POST /api/command`: Accepts JSON commands (e.g., `{"target": "main", "cmd": "RELAY_ON"}`).
- `GET /`: Serves the dashboard UI.

## 6. Acceptance Criteria
- Dashboard loads at `http://localhost:5000`.
- TDS graph updates every second without page reload.
- Clicking "Relay Toggle" sends a request to the backend.
- UI remains responsive on mobile/tablet.
