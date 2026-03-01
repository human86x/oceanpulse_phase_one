# SPEC-022: Lab Center Infrastructure & Connectivity

**Status:** APPROVED
**Priority:** HIGH
**Owner:** Systems_Architect (spec), DevOps_Engineer (implementation)
**Created:** 2026-02-17
**References:** SPEC-001 (Obs Center), SPEC-021 (Kiosk)

---

## 1. Purpose
Define the connectivity requirements for the `lab-center` Pi (System D - 192.168.43.236). This ensures the Observational Center has reliable network access and complies with site-specific networking constraints.

---

## 2. WiFi Network Configurations

The Lab Center Pi must automatically connect to the following networks:

### 2.1 Network: Martinhal
- **SSID:** `Martinhal*` (Open network, SSID prefix match if exact SSID is ambiguous)
- **Security:** None (Open)
- **Priority:** Standard (0)

### 2.2 Network: DIRECT-Ez-WP6 (Primary)
- **SSID:** `DIRECT-Ez-WP6`
- **Security:** WPA2-PSK
- **Password:** `vYiLs9sL`
- **Priority:** High (100) - This network MUST be preferred over others.
- **Proxy Configuration:** 
  - **Scope:** ONLY for this specific network.
  - **Type:** HTTP/HTTPS
  - **Host:** `192.168.49.1`
  - **Port:** `8228`

---

## 3. Implementation Requirements

### 3.1 Network Manager (nmcli)
Implementation should use `nmcli` if supported by the OS (standard on Pi OS Bookworm/Bullseye).

### 3.2 Proxy Implementation
The proxy must be network-specific. 
- If using `nmcli`, use `proxy.method manual` and relevant proxy fields.
- Alternatively, use a NetworkManager dispatcher script to set/unset environment variables (`http_proxy`, `https_proxy`) when this specific UUID is activated.

### 3.3 Persistence
Configurations must persist across reboots.

---

## 4. Success Criteria
- [ ] Lab Center Pi connects to `DIRECT-Ez-WP6` automatically when available.
- [ ] `DIRECT-Ez-WP6` is chosen over `Martinhal` if both are visible.
- [ ] Internet/Network traffic routed via `192.168.49.1:8228` ONLY when on `DIRECT-Ez-WP6`.
- [ ] Connectivity to `Martinhal` works without proxy settings.
