# Lab Router Configuration

This document details the configuration of the `lab-router` machine at `router@10.42.0.1`. The goal is to set up a dual-interface router: one adapter for external WiFi (client mode) and another for creating a hotspot ("lab-wifi").

## Hardware Identification (Current State)

The `lab-router` has **two Ralink RT3070 USB WiFi adapters** (using the `rt2800usb` driver).

*   **`wlx005a8f315136`**: Client interface.
    *   **Connection**: Connected to `MEO-80C110`.
    *   **Management**: NetworkManager.
    *   **Role**: Internet access.

*   **`wlx78d38d13802b`**: Hotspot interface.
    *   **Role**: AP for "lab-wifi".
    *   **Status**: Driver conflict (`nl80211` error) preventing `hostapd` from starting reliably.
    *   **IP**: Configured as `192.168.4.1` (static).

## Router Control Panel

A Flask-based web control panel has been installed to manage the router.

*   **Location**: `/home/router/panel`
*   **Service**: `router-panel.service` (Auto-starts at boot)
*   **URL**: `http://10.42.0.1` (Accessible from connected networks)
*   **Port**: 80

### Features
1.  **Hotspot Configuration**: Edit SSID and Password for the "lab-wifi" hotspot.
    *   *Note*: Applying changes restarts the `hostapd` service.
2.  **Connected Clients**: Visualizes devices connected to the hotspot (reads `dnsmasq` leases).
3.  **Network Scanner**: Scans for available external Wi-Fi networks using the client interface and allows connecting to them.

## Manual Configuration Details

*   **Hotspot Config**: `/etc/hostapd/hostapd.conf`
*   **DHCP Config**: `/etc/dnsmasq.conf`
*   **Network Interfaces**: `/etc/network/interfaces` (Static IP for hotspot)
*   **NetworkManager**: Configured to ignore `wlx78d38d13802b` in `/etc/NetworkManager/NetworkManager.conf`.

## Troubleshooting

*   **Hotspot Failure**: If `lab-wifi` is not visible, check `systemctl status hostapd`. The `rt2800usb` driver often reports "Operation already in progress" due to conflicts with other processes (like `wpa_supplicant`).
*   **Panel Access**: Ensure you are connected to the router via Ethernet or the working Wi-Fi link to access `http://10.42.0.1`.