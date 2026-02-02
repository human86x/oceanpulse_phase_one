# Dev-Core Hub Schematics

This directory contains the visual architectural representations of the Dev-Core Hub system.

## System Architecture Diagram

The following diagram illustrates the network topology, hardware components, and data flow within the system.

```mermaid
graph TD
    %% Nodes and Subgraphs
    Internet((Internet))
    
    subgraph Gateway_Pi [Gateway Pi (Zero W)]
        Wlan0_Wan[wlan0 (WAN)<br/>DHCP Client]
        Uap0_Lan[uap0 (LAN)<br/>192.168.50.1]
        Services[Hostapd, Dnsmasq,<br/>IPTables NAT]
    end

    subgraph Private_Net [Private Dev Network (WiFi)]
        NetBus{SSID: DevCore_Net<br/>192.168.50.0/24}
    end

    subgraph Worker_Pi [Worker Pi (Pi 3)]
        Eth0_Work[eth0 / wlan0<br/>192.168.50.10]
        DevTools[Gemini CLI, Docker,<br/>Python, SSH Server]
        UsbHost[USB Host Controller]
    end

    subgraph Peripherals [Hardware Peripherals]
        UsbHub[Powered USB Hub]
        Arduino[Arduino Board]
        Webcam[Webcam]
        Mic[Microphone]
    end

    subgraph User_Device [User Device]
        Laptop[Laptop/Tablet<br/>DHCP: 192.168.50.x]
    end

    %% Connections
    Internet <-->|WiFi| Wlan0_Wan
    Wlan0_Wan --- Services
    Services -->|Routing/NAT| Uap0_Lan
    Uap0_Lan -->|Broadcasts| NetBus
    
    NetBus <-->|WiFi Connection| Eth0_Work
    NetBus <-->|WiFi Connection| Laptop

    Eth0_Work --- DevTools
    Eth0_Work --- UsbHost
    UsbHost --- UsbHub
    UsbHub --- Arduino
    UsbHub --- Webcam
    UsbHub --- Mic

    %% Styling
    classDef net fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef pi fill:#fce4ec,stroke:#880e4f,stroke-width:2px;
    classDef device fill:#f0f4c3,stroke:#827717,stroke-width:2px;
    
    class Gateway_Pi,Worker_Pi pi;
    class Private_Net net;
    class User_Device,Peripherals device;
```

## Key Components

1.  **Gateway Pi:** The entry point. It bridges your home WiFi to the private `192.168.50.x` network.
2.  **Worker Pi:** The brain. It sits on the private network and runs all development tools.
3.  **Peripherals:** Connected via a powered USB hub to the Worker Pi, ensuring the Pi itself isn't power-drained.
