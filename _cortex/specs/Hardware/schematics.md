---
config:
  theme: redux
---
graph TD
    %% ==========================================
    %% CENTRAL POWER BANK
    %% ==========================================
    subgraph PowerBank[Central Power Source]
        Solar[Solar Panel Array] --> MPPT[MPPT Charge Controller]
        MPPT --> Batt[LiFePO4 Battery Bank]
        Batt --> MainBus((12V Common Bus))
    end
    
    %% ==========================================
    %% SYSTEM A: MISSION CIRCUIT
    %% ==========================================
    subgraph SysA[SYSTEM A: MISSION CIRCUIT]
        %% Power Input A
        MainBus --> RelayB_Contact[NC Relay B Contact]
        RelayB_Contact --> BuckA[5V Buck Converter A]
        BuckA --> Pi5[Raspberry Pi 5]
        BuckA --> ArdA[Arduino A]
        
        %% Components A
        Pi5 -- CSI --> Cam[Pi Camera 3]
        Pi5 -- USB --> ArdA
        
        %% Vision Hardware
        ArdA -- PWM --> MOSFET_A[MOSFET Driver]
        MOSFET_A --> UV_LED[365nm UV LED]
        
        %% Underwater Sensors
        subgraph WaterSensors[Underwater Sensors]
            DO[Dissolved Oxygen] --> ArdA
            Sal[Salinity] --> ArdA
            TempA[Water Temp] --> ArdA
            Depth[Depth/Pressure] --> ArdA
            Flow[Current Meter] --> ArdA
        end
        
        %% Comms A
        Pi5 -- SPI --> LoRaA[LoRa Module A]
        LoRaA -.->|"Mission Data"| OnshoreGateway
        
        %% WATCHDOG OUTPUT A
        ArdA -- Digital Out --> RelayA_Coil[Relay A Coil]
    end
    
    %% ==========================================
    %% SYSTEM B: HEALTH CIRCUIT
    %% ==========================================
    subgraph SysB[SYSTEM B: HEALTH CIRCUIT]
        %% Power Input B
        MainBus --> RelayA_Contact[NC Relay A Contact]
        RelayA_Contact --> BuckB[5V Buck Converter B]
        BuckB --> Pi3[Raspberry Pi 3]
        BuckB --> ArdB[Arduino B]
        
        %% Components B
        Pi3 -- USB --> ArdB
        
        %% Internal Environment Sensors
        subgraph InternalSensors[Internal Health]
            Hum[Humidity] --> ArdB
            TempB[Internal Temp] --> ArdB
            Volt[Voltage Sensor] -->|"Reads Main Bus"| ArdB
            Leak[Bilge Switch] --> ArdB
        end
        
        %% Comms B
        Pi3 -- SPI --> LoRaB[LoRa Module B]
        LoRaB -.->|"Health/Cmds"| OnshoreGateway
        
        %% WATCHDOG OUTPUT B
        ArdB -- Digital Out --> RelayB_Coil[Relay B Coil]
    end
    
    %% ==========================================
    %% CROSS-WATCHDOG CONNECTIONS
    %% ==========================================
    %% Relay A (Controlled by Sys A) cuts power to Sys B
    RelayA_Coil -.->|"Controls"| RelayA_Contact
    
    %% Relay B (Controlled by Sys B) cuts power to Sys A
    RelayB_Coil -.->|"Controls"| RelayB_Contact
    
    %% ==========================================
    %% STYLING
    %% ==========================================
    classDef pwr fill:#f96,stroke:#333,stroke-width:2px;
    classDef sbc fill:#69f,stroke:#333,stroke-width:2px,color:white;
    classDef mcu fill:#6f9,stroke:#333,stroke-width:2px;
    classDef sens fill:#fff,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5;
    classDef relay fill:#f66,stroke:#333,stroke-width:2px,color:white;
    
    class Solar,MPPT,Batt,MainBus,BuckA,BuckB pwr;
    class Pi5,Pi3 sbc;
    class ArdA,ArdB mcu;
    class WaterSensors,InternalSensors sens;
    class RelayA_Coil,RelayB_Coil,RelayA_Contact,RelayB_Contact relay;