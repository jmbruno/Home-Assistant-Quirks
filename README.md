## This quirks is for modules zigbee not define in ZHA

### Quirk for Micro waves sensor TS0601 _TZE284_gnpflcoq
<img width="220" height="220" alt="image" src="https://github.com/user-attachments/assets/88cd77a3-19fc-4e9b-bec6-67b50acd31ce" />

### Quirk for Energy Meter dual TC TS0601 _TZE204_81yrt3lo
<img width="220" height="220" alt="image" src="https://github.com/user-attachments/assets/deb923a6-f3a8-4288-95cc-be14d7511d2a" />

## Enabling custom quirks in Home Assistant

 1. Create a folder called custom_zha_quirks in your Home Assistant configuration directory (/config/custom_zha_quirks).

 2. Add the path declaration to your "configuration.yaml" file:
      ### zha:
    
      ###   custom_quirks_path: /config/custom_zha_quirks/
      ###
 4. Add your file(s)
