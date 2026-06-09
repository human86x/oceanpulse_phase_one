# OceanPulse — Phase 1

> Autonomous coastal water-quality and oil-spill monitoring buoy for the
> Port of Sagres, Portugal.

OceanPulse is a solar-powered, radio-linked sensing platform that monitors
water quality, captures camera frames of the sea surface, and runs an
active UV-fluorescence test for hydrocarbon contamination. Telemetry is
relayed from the buoy over LoRa to an onshore gateway and pushed to a
public observational center on the open internet.

This repository holds the **Phase 1 prototype** — the work-package that
takes the system from bench validation to a deployed unit at the Port of
Sagres.

---

## Status

| Item | State |
|---|---|
| Firmware (main + health Megas) | v3.7 / v2.1 — stable |
| Software stack (bridges, obs center, vision) | Feature-complete for Phase 1 |
| Hardware integration | Build complete; UV safety interlock final tuning pending |
| Deployment | Pre-deployment, pending final port logistics |

The build is essentially done. The remaining open item is the UV safety
interlock calibration; everything else is in soak-test mode.

---

## Architecture

```
        +-------------------------+
        |   BUOY  (offshore)      |
        |                         |
        | Pi 5 ── Main Mega ── Water sensors (EC / DO / pH / Depth)
        |  │       │                │
        |  │       │                └─ Camera (vision)
        |  │       └─ UV strobe + PIR + ultrasonic (safety interlock)
        |  │
        |  Pi 3 ── Health Mega ── Battery / temp / humidity
        |  │
        |  LoRa radio (M circuit + H circuit)
        +-------------------------+
                     │
                  LoRa link
                     │
        +-------------------------+
        |   ONSHORE  (gateway)    |
        |  Pi ── LoRa receiver    |
        |        └─ 4G uplink     |
        +-------------------------+
                     │
                   HTTPS
                     │
        +-------------------------+
        |   OBS CENTER  (VPS)     |
        |  Flask backend          |
        |  + public dashboard     |
        +-------------------------+
                     │
                     ▼
              oceanpulse.pt
```

### Dual-Circuit Redundancy

The buoy carries two independent radio paths — the **Main** circuit (Pi 5
+ main Mega + water-quality sensors) and the **Health** circuit (Pi 3 +
health Mega + battery/environment sensors). Each has its own LoRa radio
on a different frequency slot. Either circuit can keep the buoy reachable
if the other dies.

---

## Repository Layout

```
bridge/         Python services that ferry data between Arduino, LoRa
                radio, and the obs center
comms/          LoRa diagnostic + tuning tools
firmware/
  main_mega/    Main-circuit Arduino firmware (v3.7)
  health_mega/  Health-circuit Arduino firmware (v2.1)
obs_center/     Flask backend, dashboard, REST API
vision/         Camera capture + frame analysis service
ops/            Deploy scripts, systemd units, secrets template
web_presentation/
  dashboard/    Public dashboard served from oceanpulse.pt
  deployment/   Internal roadmap/planning panel
hardware/
  electrical/   System wiring diagrams (Mermaid)
```

---

## Hardware

| Layer | Component |
|---|---|
| Compute | 2× Raspberry Pi (Main: Pi 5 / Health: Pi 3) |
| MCU | 2× Arduino Mega 2560 |
| Water quality | Atlas Scientific EZO EC + DO, Bar30 depth, pH |
| Vision | USB camera (above-water, downward-facing) |
| Oil detection | UV-A strobe + camera (fluorescence) with PIR + ultrasonic safety interlock |
| Comms | EBYTE E22 LoRa modules (2 channels) + 4G LTE on gateway |
| Power | 100 W solar panels → Victron MPPT → 50 Ah LiFePO4 + SmartShunt monitoring |

---

## Deployment

The production stack runs on four nodes accessed via Tailscale:

- **Main Pi** (buoy) — main bridge + vision service
- **Health Pi** (buoy) — health bridge + power bridge
- **Onshore Gateway Pi** — LoRa receiver + 4G uplink
- **VPS** — public obs center (Flask + dashboard)

### Secrets

All credentials (SSH passwords, FTP, admin login, Flask session key) live
in `ops/secrets.env`, which is gitignored. Use
`ops/secrets.env.example` as the schema.

Systemd loads them via `EnvironmentFile=` (see `ops/obs-center.service`).
Shell deploy scripts source them at the top.

### Quickstart (on a fresh node)

```bash
cp ops/secrets.env.example ops/secrets.env
# fill in real values
./ops/deploy_obs_center.sh    # for the VPS / obs center
./ops/deploy_vision.sh        # for the main Pi
./firmware/deploy.sh all      # flash both Megas
```

See `OCEANPULSE_DEPLOYMENT.md` for the public-dashboard FTP path.

---

## License

All rights reserved. This repository is published for transparency around
the Phase 1 deployment; reuse of the design or code requires written
permission. Contact `info@oceanpulse.pt`.
