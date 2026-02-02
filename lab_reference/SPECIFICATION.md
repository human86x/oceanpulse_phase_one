# SPECIFICATION: Dev-Core Hub

**Version:** 1.0
**Project Status:** Design

## 1. Overview

This document outlines the technical specification for the "Dev-Core Hub," a self-contained, portable system designed to serve as the heart of a development workspace. The system provides a private, managed network, a dedicated development machine, and a platform for future IoT/automation projects.

The primary goal is to create a reproducible and stable environment that can be used for various software projects, device configuration, and network control, independent of the external network environment.

## 2. System Architecture

The architecture is based on a two-Raspberry Pi model: a **Gateway Pi** for networking and a **Worker Pi** for computation and control.

### 2.1. Conceptual Diagram

```
      (Your Home/Office Internet)
                  | (WiFi)
+------------------------------------+
|         Gateway Pi (Pi 3 B+)       |
|  - Runs Router/AP Software         |
|  - Manages Private Dev Network     |
|  - DHCP/Firewall (192.168.50.1)    |
|  - Interfaces:                     |
|    * wlan0: WAN (Internet)         |
|    * eth0: LAN (Wired Link)        |
|    * wlan1: LAN (WiFi AP)          |
+------------------------------------+
                  | (Ethernet)
+------------------------------------+
|        Private Dev Network         |
|        (192.168.50.0/24)           |
+------------------------------------+
                  |
            +--------------+
            |  Worker Pi   |
            |    (Pi 5)    |
            | 192.168.50.10|
            +--------------+
                  | (USB)
                  |
    +------------------------------------+
    |            USB Hub                 |
    | - Peripherals, Drives, etc.        |
    +------------------------------------+

(Optional WiFi Clients connect to 'DevCore_Net' via Gateway's wlan1)
```

### 2.2. Component Roles

-   **Gateway Pi (Raspberry Pi 3 Model B+):** Functions as the network router.
    -   **WAN:** Connects to an existing WiFi network via internal WiFi (`wlan0`) for internet access.
    -   **LAN (Wired):** Connects to the Worker Pi via Ethernet (`eth0`), providing a high-speed, stable link.
    -   **LAN (Wireless):** Creates a private WiFi Access Point (`DevCore_Net`) using the TP-Link USB adapter (`wlan1`) for other wireless devices (laptops, IoT).
    -   **Services:** Handles DHCP, DNS, and NAT for the private network.
-   **Worker Pi (Raspberry Pi 5):** The main development workstation and control server.
    -   **Performance:** Leverages the Pi 5's quad-core processor and 4GB RAM for intensive tasks.
    -   **Cooling:** Equipped with the Pi Active Cooler to maintain performance under load.
    -   **Connectivity:** Connects directly to the Gateway via Ethernet for low-latency access.
    -   **Function:** Runs the Gemini CLI, build tools, Docker containers, and orchestration scripts.
-   **USB Hub:** Attached to the Worker Pi to expand connectivity for peripherals (keyboard, mouse, sensors).
-   **Enclosure:** Separate cases for Pi 3 and Pi 5 (Official Pi 3 Case, JOY-IT Aluminum Pi 5 Case).

## 3. Hardware Bill of Materials (BOM)

| Code | Component | Qty | Total Price |
| :--- | :--- | :---: | :---: |
| 095-5004 | Microcomputador Raspberry Pi 5 4GB | 1 | € 68,88 |
| 096-5700 | Microcomputador Raspberry Pi 3 Model B+ 1GB | 1 | € 39,86 |
| 035-5179 | Goobay 4×USB-A Charger (30W) | 2 | € 17,98 |
| 047-5056 | Vention HUB USB 3.0 (4 ports, powered) | 1 | € 13,25 |
| 047-4783 | MicroSD HC Card (32GB, Class A2) | 2 | € 13,31 |
| 047-0309 | TP-Link Pen USB Wireless N 150Mbps | 1 | € 9,61 |
| 047-2944 | Pi HDMI 2.0 Cable (Micro-HDMI to HDMI) | 2 | € 9,89 |
| 095-2493 | Pi Active Cooler (SC1148) - Pi 5 | 1 | € 5,99 |
| 096-3973 | Pi Official Case (Pi 3 B/B+) | 1 | € 5,99 |
| 095-3448 | JOY-IT Case for Raspberry Pi 5 (Alum.) | 1 | € 6,33 |
| 047-5205 | Ewent EW3112 - Teclado USB c/ Hotkey | 1 | € 5,35 |
| 096-4603 | Adaptador Mini-HDMI (M) para HDMI (F) | 2 | € 4,21 |
| 047-4875 | Pi Official USB-A to Micro-USB Cable | 2 | € 3,42 |
| 047-2386 | Leitor USB2.0 MicroSD Card Reader | 1 | € 3,75 |
| 047-3801 | Maxlife MXHM-01 - Rato óptico USB | 1 | € 2,23 |
| 095-5281 | Equip - Tapete de rato standard | 1 | € 1,88 |
| 015-0606 | Cabo de rede RJ45 CAT6 U/UTP 0.25m | 1 | € 0,82 |
| **TOTAL** | | **17** | **€ 237,85** |

## 4. Software and Configuration

### 4.1. Gateway Pi (Raspberry Pi 3 Model B+)

-   **Operating System:** Raspberry Pi OS Lite (latest stable version).
-   **Hostname:** `gateway`
-   **Function:** Network Router, Firewall, and Access Point.

#### Networking Configuration:

1.  **WAN Interface (`wlan0` - Internal WiFi):**
    -   **Configuration:** DHCP Client.
    -   **Purpose:** Uplink to the internet (Home/Office WiFi).
    -   **Setup:** Configure via `wpa_supplicant` or NetworkManager.

2.  **LAN Interface 1 (`eth0` - Wired):**
    -   **Configuration:** Static IP Address.
    -   **IP Address:** `192.168.50.1`
    -   **Netmask:** `255.255.255.0`
    -   **Purpose:** Primary high-speed link to the Worker Pi.

3.  **LAN Interface 2 (`wlan1` - USB WiFi Adapter):**
    -   **Configuration:** Static IP Address.
    -   **IP Address:** `192.168.50.2` (or bridged to `192.168.50.1` if using a bridge, but separate subnet or routing is simpler without bridge utils. For simplicity here, we will route).
    -   *Refined Design:* To keep all devices on the *same* subnet (`192.168.50.x`), a **Network Bridge (`br0`)** is recommended combining `eth0` and `wlan1`.
    -   **Bridge Interface (`br0`):**
        -   **IP Address:** `192.168.50.1`
        -   **Members:** `eth0`, `wlan1` (hostapd managed).

#### Core Services:

1.  **`hostapd` (Access Point Service):**
    -   **Configuration File:** `/etc/hostapd/hostapd.conf`
    -   **SSID:** `DevCore_Net`
    -   **Password:** `DevCorePass` (Change immediately).
    -   **Interface:** `wlan1` (The TP-Link USB Adapter).
    -   **Driver:** `nl80211` (Ensure driver support for the specific USB dongle chipset).
    -   **Bridge:** `br0` (Add `bridge=br0` to config to bridge wireless clients to Ethernet).

2.  **`dnsmasq` (DHCP and DNS Service):**
    -   **Configuration File:** `/etc/dnsmasq.conf`
    -   **Interface:** `br0` (The bridge interface).
    -   **DHCP Range:** `192.168.50.100,192.168.50.200,12h`
    -   **Gateway:** `192.168.50.1`
    -   **DNS:** Forward upstream (Google 8.8.8.8 or ISP).

3.  **Routing and NAT:**
    -   Enable IP forwarding: `net.ipv4.ip_forward=1`.
    -   **NAT Rule:** Masquerade traffic leaving via `wlan0`.
        ```bash
        sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
        ```
    -   **Forwarding Rules:** Allow traffic between Bridge (LAN) and WiFi (WAN).
        ```bash
        sudo iptables -A FORWARD -i wlan0 -o br0 -m state --state RELATED,ESTABLISHED -j ACCEPT
        sudo iptables -A FORWARD -i br0 -o wlan0 -j ACCEPT
        ```

### 4.2. Worker Pi (Raspberry Pi 5)

-   **Operating System:** Raspberry Pi OS with Desktop (Bookworm 64-bit).
-   **Hostname:** `worker`
-   **Function:** Main development and control machine.

#### Networking Configuration:

1.  **Primary Interface (`eth0`):**
    -   **Configuration:** Static IP Address.
    -   **IP Address:** `192.168.50.10`
    -   **Netmask:** `255.255.255.0`
    -   **Gateway:** `192.168.50.1` (The Gateway Pi)
    -   **DNS Server:** `192.168.50.1`

#### Hardware Configuration:

-   **Cooling:** Ensure the "Pi Active Cooler" is installed and the fan profile is active (usually automatic in OS).
-   **Power:** Connect to the 30W USB-A Charger. Note: For maximum peak performance, a 5V/5A USB-C PD supply is ideal, but the Pi 5 will operate on standard USB-C power (3A) with restricted USB peripheral current.
-   **Peripherals:** Connect high-power USB devices to the external **Powered USB Hub** to avoid overloading the Pi's USB ports, especially given the power supply constraints.

#### Core Software & Tools:

-   **Gemini CLI:** Installed and configured for use.
-   **SSH Server:** Enabled by default (`raspi-config`).
-   **SSH Client:** Installed by default.
--  **Passwordless SSH:** An SSH key pair should be generated on the `worker` Pi. The public key must be copied to the `~/.ssh/authorized_keys` file on the `gateway` Pi.
-   **Standard Dev Tools:**
    -   `git`
    -   `python3`, `pip` (Use a virtual environment `venv` as per PEP 668).
    -   `nodejs`, `npm`
    -   `docker` and `docker-compose`

## 5. Future Expansion Specification

-   **Audio/Video Input:**
    -   **Hardware:** A USB microphone and/or webcam will be connected to the powered USB hub attached to the **Worker Pi**.
    -   **Software:** The **Worker Pi** will run analysis software.
        -   For audio: `PyAudio` or similar libraries.
        -   For video: `OpenCV` (Python bindings) or similar libraries.

-   **Environment Control:**
    -   **Hardware:** An Arduino board will be connected via USB to the **Worker Pi**. Relays or other actuators will be connected to the Arduino's GPIO pins.
    -   **Software:** The **Worker Pi** will run a Python script using the `pyserial` library to send control commands to the Arduino over the USB/serial connection. The Arduino will run a simple sketch to parse these commands and control its GPIO pins accordingly.

---
*This specification provides a complete blueprint for the construction and configuration of the Dev-Core Hub. All implementation steps should adhere to this document.*