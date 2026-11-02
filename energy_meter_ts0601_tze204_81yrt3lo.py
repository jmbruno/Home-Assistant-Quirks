"""ZHA quirk for the Tuya TS0601 MatSeePlus dual-CT energy meter."""

from __future__ import annotations

from typing import Any

import zigpy.types as t
from zigpy.zcl.clusters.homeautomation import MeasurementType

from zhaquirks.tuya import (
    TuyaLocalCluster,
    TuyaZBElectricalMeasurement,
    TuyaZBMeteringClusterWithUnit,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster

ENDPOINT_CT_B = 2
ENDPOINT_TOTAL = 3


class EnergyFlow(t.enum8):
    """Direction encoded by the device."""

    FORWARD = 0
    REVERSE = 1


class MatSeePlusElectricalMeasurement(TuyaZBElectricalMeasurement, TuyaLocalCluster):
    """Electrical measurements reported for either current transformer."""

    _VALID_ATTRIBUTES = {
        TuyaZBElectricalMeasurement.AttributeDefs.active_power.id,
        TuyaZBElectricalMeasurement.AttributeDefs.power_factor.id,
        TuyaZBElectricalMeasurement.AttributeDefs.rms_current.id,
    }
    _CONSTANT_ATTRIBUTES = {
        **TuyaZBElectricalMeasurement._CONSTANT_ATTRIBUTES,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 10,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency_multiplier.id: 1,
        TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 100,
        TuyaZBElectricalMeasurement.AttributeDefs.measurement_type.id: (
            MeasurementType.Active_measurement_AC
            | MeasurementType.Phase_A_measurement
        ),
    }


class MatSeePlusTotalElectricalMeasurement(
    TuyaZBElectricalMeasurement, TuyaLocalCluster
):
    """Shared voltage/frequency and combined power measurement."""

    _CONSTANT_ATTRIBUTES = {
        **MatSeePlusElectricalMeasurement._CONSTANT_ATTRIBUTES,
        TuyaZBElectricalMeasurement.AttributeDefs.measurement_type.id: (
            MeasurementType.Active_measurement_AC
        ),
    }
    _VALID_ATTRIBUTES = {
        TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency.id,
        TuyaZBElectricalMeasurement.AttributeDefs.rms_voltage.id,
        TuyaZBElectricalMeasurement.AttributeDefs.total_active_power.id,
    }


class MatSeePlusMetering(TuyaZBMeteringClusterWithUnit, TuyaLocalCluster):
    """Import/export energy counters for one clamp."""

    _VALID_ATTRIBUTES = {
        TuyaZBMeteringClusterWithUnit.AttributeDefs.current_summ_delivered.id,
        TuyaZBMeteringClusterWithUnit.AttributeDefs.current_summ_received.id,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(
            TuyaZBMeteringClusterWithUnit.AttributeDefs.instantaneous_demand.id
        )


class MatSeePlusManufacturerCluster(TuyaMCUCluster):
    """Translate power direction and publish the corrected combined power."""

    _POWER_DP = {
        "power_a": (1, "energy_flow_a"),
        "power_b": (ENDPOINT_CT_B, "energy_flow_b"),
    }
    _FLOW_DP = {
        "energy_flow_a": "power_a",
        "energy_flow_b": "power_b",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._flow = {
            "energy_flow_a": EnergyFlow.FORWARD,
            "energy_flow_b": EnergyFlow.FORWARD,
        }
        self._raw_power: dict[str, int | None] = {
            "power_a": None,
            "power_b": None,
        }
        self._signed_power = {1: 0, ENDPOINT_CT_B: 0}
        super().__init__(*args, **kwargs)

    @property
    def _flow_is_delayed(self) -> bool:
        """The TZE204 firmware reports each flow direction one interval late."""
        return self.endpoint.device.manufacturer == "_TZE204_81yrt3lo"

    def _publish_power(self, power_dp: str, direction: EnergyFlow) -> None:
        endpoint_id, _ = self._POWER_DP[power_dp]
        value = self._raw_power[power_dp]
        if value is None:
            return

        signed_value = -value if direction == EnergyFlow.REVERSE else value
        self._signed_power[endpoint_id] = signed_value
        self.endpoint.device.endpoints[endpoint_id].electrical_measurement.update_attribute(
            TuyaZBElectricalMeasurement.AttributeDefs.active_power.name,
            signed_value,
        )
        self.endpoint.device.endpoints[ENDPOINT_TOTAL].electrical_measurement.update_attribute(
            TuyaZBElectricalMeasurement.AttributeDefs.total_active_power.name,
            sum(self._signed_power.values()),
        )

    def update_attribute(self, attr_name: str, value: Any) -> None:
        """Handle the two power DPs and their corresponding flow indicators."""
        if attr_name in self._POWER_DP:
            _, flow_dp = self._POWER_DP[attr_name]
            self._raw_power[attr_name] = int(value)
            if not self._flow_is_delayed or value == 0:
                self._publish_power(attr_name, self._flow[flow_dp])
        elif attr_name in self._FLOW_DP:
            self._flow[attr_name] = EnergyFlow(value)
            if self._flow_is_delayed:
                self._publish_power(self._FLOW_DP[attr_name], self._flow[attr_name])

        super().update_attribute(attr_name, value)


(
    TuyaQuirkBuilder("_TZE204_81yrt3lo", "TS0601")
    .applies_to("_TZE284_81yrt3lo", "TS0601")
    .tuya_enchantment()
    .adds_endpoint(ENDPOINT_CT_B)
    .adds_endpoint(ENDPOINT_TOTAL)
    .adds(MatSeePlusElectricalMeasurement)
    .adds(MatSeePlusElectricalMeasurement, endpoint_id=ENDPOINT_CT_B)
    .adds(MatSeePlusTotalElectricalMeasurement, endpoint_id=ENDPOINT_TOTAL)
    .adds(MatSeePlusMetering)
    .adds(MatSeePlusMetering, endpoint_id=ENDPOINT_CT_B)
    # Import/export energy, in hundredths of a kWh.
    .tuya_dp(
        dp_id=106,
        ep_attribute=MatSeePlusMetering.ep_attribute,
        attribute_name=MatSeePlusMetering.AttributeDefs.current_summ_delivered.name,
    )
    .tuya_dp(
        dp_id=107,
        ep_attribute=MatSeePlusMetering.ep_attribute,
        attribute_name=MatSeePlusMetering.AttributeDefs.current_summ_received.name,
    )
    .tuya_dp(
        dp_id=108,
        ep_attribute=MatSeePlusMetering.ep_attribute,
        attribute_name=MatSeePlusMetering.AttributeDefs.current_summ_delivered.name,
        endpoint_id=ENDPOINT_CT_B,
    )
    .tuya_dp(
        dp_id=109,
        ep_attribute=MatSeePlusMetering.ep_attribute,
        attribute_name=MatSeePlusMetering.AttributeDefs.current_summ_received.name,
        endpoint_id=ENDPOINT_CT_B,
    )
    # Power and flow are processed together by the manufacturer cluster.
    .tuya_dp_attribute(dp_id=101, attribute_name="power_a", type=t.uint32_t_be)
    .tuya_dp_attribute(dp_id=102, attribute_name="energy_flow_a", type=EnergyFlow)
    .tuya_dp_attribute(dp_id=104, attribute_name="energy_flow_b", type=EnergyFlow)
    .tuya_dp_attribute(dp_id=105, attribute_name="power_b", type=t.uint32_t_be)
    .tuya_dp(
        dp_id=110,
        ep_attribute=MatSeePlusElectricalMeasurement.ep_attribute,
        attribute_name=TuyaZBElectricalMeasurement.AttributeDefs.power_factor.name,
    )
    .tuya_dp(
        dp_id=121,
        ep_attribute=MatSeePlusElectricalMeasurement.ep_attribute,
        attribute_name=TuyaZBElectricalMeasurement.AttributeDefs.power_factor.name,
        endpoint_id=ENDPOINT_CT_B,
    )
    .tuya_dp(
        dp_id=113,
        ep_attribute=MatSeePlusElectricalMeasurement.ep_attribute,
        attribute_name=TuyaZBElectricalMeasurement.AttributeDefs.rms_current.name,
    )
    .tuya_dp(
        dp_id=114,
        ep_attribute=MatSeePlusElectricalMeasurement.ep_attribute,
        attribute_name=TuyaZBElectricalMeasurement.AttributeDefs.rms_current.name,
        endpoint_id=ENDPOINT_CT_B,
    )
    .tuya_dp(
        dp_id=112,
        ep_attribute=MatSeePlusTotalElectricalMeasurement.ep_attribute,
        attribute_name=TuyaZBElectricalMeasurement.AttributeDefs.rms_voltage.name,
        endpoint_id=ENDPOINT_TOTAL,
    )
    .tuya_dp(
        dp_id=111,
        ep_attribute=MatSeePlusTotalElectricalMeasurement.ep_attribute,
        attribute_name=TuyaZBElectricalMeasurement.AttributeDefs.ac_frequency.name,
        endpoint_id=ENDPOINT_TOTAL,
    )
    .add_to_registry(replacement_cluster=MatSeePlusManufacturerCluster)
)
