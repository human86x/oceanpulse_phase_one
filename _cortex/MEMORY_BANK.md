# Shared Memory Bank

## Remote Access (Tailscale VPN -- works from anywhere)
> **PREFERRED ROUTE:** Always use Tailscale IPs for SSH/deploy. These work from any network worldwide.
> Local IPs only work when on the same WiFi (TP-Link_C7E2 / 192.168.1.x).

| System | Hostname | Tailscale IP | User | Pass |
|--------|----------|-------------|------|------|
| A (Main Mission) | main | `100.115.88.91` | lab | 777 |
| B (Health/Router) | lab-router | `100.116.100.92` | router | 777 |
| C (Onshore Gateway) | node1 | `100.64.151.40` | node1 | 777 |
| D (Lab Center) | lab-center | `100.77.91.123` | lab | 777 |
| Dev Laptop | dev-laptop | `100.87.135.125` | human | - |

## System A (Main Mission)
*   **Hostname:** main
*   **Tailscale IP:** 100.115.88.91
*   **Local IP:** 192.168.1.104 (TP-Link_C7E2)
*   **User:** lab
*   **Pass:** 777
*   **USB:** /dev/ttyACM0 (Arduino Mega)

## System B (Health/Router)
*   **Hostname:** lab-router
*   **Tailscale IP:** 100.116.100.92
*   **Local IP:** 192.168.1.103 (TP-Link_C7E2)
*   **User:** router
*   **Pass:** 777

## System C (Onshore Gateway)
*   **Hostname:** node1
*   **Tailscale IP:** 100.64.151.40
*   **Local IP:** 192.168.1.105 (TP-Link_C7E2)
*   **User:** node1
*   **Pass:** 777

## System D (Lab Center)
*   **Hostname:** lab-center
*   **Tailscale IP:** 100.77.91.123
*   **Local IP:** DHCP (TP-Link_C7E2 + Martinhal) — use `nmap -sn 192.168.1.0/24` to find
*   **User:** lab
*   **Pass:** 777

## Hardware Map
*   **Relay:** Pin 2 (Arduino Mega)
*   **TDS Sensor:** Pin A0 (Arduino Mega)

## ADT Panel Hosting (oceanpulse.pt)
*   **Host:** ftp.oceanpulse.pt
*   **User:** oceanpul
*   **Pass:** sagres_2025Xx
*   **Protocol:** FTP (port 21)
*   **Remote Path:** public_html/adt_panel/
*   **Public URL:** https://oceanpulse.pt/adt_panel/

