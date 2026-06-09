# OceanPulse Oil Detection Hardware Schematic

This schematic represents the **Phase 1: Port Sentry** hardware architecture, focusing on the **System A (Mission Circuit)** which handles autonomous oil spill detection using UV fluorescence and computer vision.

## System Architecture Diagram

```mermaid
graph TD
    %% ==========================================
    %% CENTRAL POWER BANK
    %% ==========================================
    subgraph PowerBank[Central Power Source]
        Solar[Solar Panel Array<br/>2x 50W Parallel] --> MPPT[MPPT Controller<br/>15A]
        MPPT --> Batt[LiFePO4 Battery<br/>12V 40Ah-60Ah]
        Batt ==> MainBus((12V Common Bus))
    end
    
    %% ==========================================
    %% SYSTEM A: MISSION CIRCUIT (Oil Detection Focus)
    %% ==========================================
    subgraph SysA[SYSTEM A: MISSION CIRCUIT]
        MainBus --> RelayB_Contact[NC Relay B Contact]
        RelayB_Contact --> BuckA[5V Buck Converter A]
        BuckA ==> Pi5[Raspberry Pi 5]
        BuckA ==> ArdA[Arduino A]
        
        Pi5 -- CSI --> Cam[Pi Camera 3 - IMX378]
        Pi5 -- USB --> ArdA
        
        ArdA -- Relay --> UV_Relay[Relay / SSR]
        UV_Relay --> UV_LED[100W UV Floodlight<br/>365nm Strobe]
        
        subgraph WaterSensors[Underwater Sensors]
            DO[Dissolved Oxygen] --> ArdA
            Sal[Salinity Inductive] --> ArdA
            TempA[Water Temp] --> ArdA
            Depth[Depth Sensor] --> ArdA
        end
        
        Pi5 -- SPI --> LoRaA[LoRa Module A]
        ArdA -- Digital --> RelayA_Coil[Relay A Coil]
    end
    
    %% ==========================================
    %% SYSTEM B: HEALTH CIRCUIT (Redundancy)
    %% ==========================================
    subgraph SysB[SYSTEM B: HEALTH CIRCUIT]
        MainBus --> RelayA_Contact[NC Relay A Contact]
        RelayA_Contact --> BuckB[5V Buck Converter B]
        BuckB ==> Pi3[Raspberry Pi 3]
        BuckB ==> ArdB[Arduino B]
        
        Pi3 -- USB --> ArdB
        
        subgraph InternalSensors[Internal Health]
            Hum[Humidity/Temp] --> ArdB
            Leak[Bilge Switch] --> ArdB
        end
        
        Pi3 -- SPI --> LoRaB[LoRa Module B]
        ArdB -- Digital --> RelayB_Coil[Relay B Coil]
    end
    
    RelayA_Coil -.->|Cuts Power| RelayA_Contact
    RelayB_Coil -.->|Cuts Power| RelayB_Contact

    classDef pwr fill:#f96,stroke:#333,stroke-width:2px;
    classDef sbc fill:#69f,stroke:#333,stroke-width:2px,color:white;
    classDef mcu fill:#6f9,stroke:#333,stroke-width:2px;
    classDef sens fill:#eee,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5;
    classDef relay fill:#f66,stroke:#333,stroke-width:2px,color:white;
    
    class Solar,MPPT,Batt,MainBus,BuckA,BuckB pwr;
    class Pi5,Pi3 sbc;
    class ArdA,ArdB mcu;
    class WaterSensors,InternalSensors sens;
    class RelayA_Coil,RelayB_Coil,RelayA_Contact,RelayB_Contact,UV_Relay relay;
```

## Component Roles in Oil Detection

| Component | Role | Details |
| :--- | :--- | :--- |
| **Raspberry Pi 5** | **Mission Intelligence** | Runs OpenCV/AI models for oil detection from camera feed. |
| **Pi Camera 3** | **Imaging Sensor** | High-resolution IMX378 sensor for capturing surface fluorescence. |
| **UV Floodlight** | **Excitation Source** | 100W 365nm LED array that causes oil to fluoresce at night. |
| **Arduino Mega (A)** | **Strobe Controller** | Triggers the UV relay for precise <1s pulses to conserve power. |
| **LiFePO4 Battery** | **Power Core** | Provides stable 12V supply for the high-power UV strobe and Pi 5. |

## Operational Logic for Detection
1. **Trigger:** System B or a timer wakes System A (Pi 5).
2. **Strobe:** Arduino A activates the UV Relay.
3. **Capture:** Pi Camera 3 takes a long-exposure frame during the UV pulse.
4. **Process:** Pi 5 analyzes the frame for specific spectral signatures of petroleum fluorescence.
5. **Alert:** If oil is detected, an alert is sent via **LoRa Module A**.
