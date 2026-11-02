"""ZHA quirk for the Tuya TS0601 4-in-1 mmWave presence sensor."""

import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.builder import SensorDeviceClass, UnitOfLength, UnitOfTime
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_motion import TuyaOccupancySensing, TuyaSensitivityMode

(
    TuyaQuirkBuilder("_TZE284_gnpflcoq", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        converter=lambda value: value == 0,
    )
    .adds(TuyaOccupancySensing)
    .tuya_battery(dp_id=4)
    .tuya_temperature(dp_id=7, scale=10)
    .tuya_humidity(dp_id=8)
    .tuya_illuminance(dp_id=11)
    .tuya_number(
        dp_id=2,
        attribute_name="radar_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="radar_sensitivity",
        fallback_name="Radar sensitivity",
    )
    .tuya_enum(
        dp_id=9,
        attribute_name="pir_sensitivity",
        enum_class=TuyaSensitivityMode,
        translation_key="pir_sensitivity",
        fallback_name="PIR sensitivity",
    )
    .tuya_number(
        dp_id=12,
        attribute_name="pir_delay",
        type=t.uint16_t,
        min_value=10,
        max_value=180,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        translation_key="pir_delay",
        fallback_name="PIR delay",
    )
    .tuya_number(
        dp_id=13,
        attribute_name="detection_range",
        type=t.uint16_t,
        min_value=1,
        max_value=10,
        step=1,
        unit=UnitOfLength.METERS,
        translation_key="detection_range",
        fallback_name="Detection range",
    )
    .skip_configuration()
    .add_to_registry()
)
