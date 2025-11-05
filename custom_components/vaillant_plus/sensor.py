"""Vaillant sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import UnitOfTemperature, UnitOfPressure
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import VaillantClient
from .const import CONF_DID, DISPATCHERS, DOMAIN, EVT_DEVICE_CONNECTED, API_CLIENT
from .entity import VaillantEntity

_LOGGER = logging.getLogger(__name__)


SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key="Room_Temperature_Setpoint_Comfort",
        name="CH temperature room setpoint comfort mode",
        translation_key="ch_temperature_set_room_comfort",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Room_Temperature_Setpoint_ECO",
        name="CH temperature room setpoint ECO mode",
        translation_key="ch_temperature_set_room_eco",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Outdoor_Temperature",
        name="CH temperature outdoor",
        translation_key="ch_temperature_outdoor",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Room_Temperature",
        name="CH temperature room",
        translation_key="ch_temperature_room",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Lower_Limitation_of_CH_Setpoint",
        name="CH temperature setpoint Lower",
        translation_key="ch_temperature_set_lower",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Upper_Limitation_of_CH_Setpoint",
        name="CH temperature setpoint Upper",
        translation_key="ch_temperature_set_upper",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Flow_Temperature_Setpoint",
        name="CH temperature flow setpoint",
        translation_key="ch_temperature_flow_set",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Flow_temperature",
        name="temperature flow current",
        translation_key="temperature_flow_current",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="return_temperature",
        name="temperature flow return",
        translation_key="temperature_flow_return",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Tank_temperature",
        name="Water tank temperature",
        translation_key="temperature_tank",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="DHW_setpoint",
        name="DHW temperature setpoint",
        translation_key="dhw_temperature_set",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Lower_Limitation_of_DHW_Setpoint",
        name="DHW temperature setpoint Lower",
        translation_key="dhw_temperature_set_lower",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Upper_Limitation_of_DHW_Setpoint",
        name="DHW temperature setpoint Upper",
        translation_key="dhw_temperature_set_upper",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Current_DHW_Setpoint",
        name="DHW temperature sepoint Current",
        translation_key="dhw_temperature_set_current",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Heating_System_Setting",
        name="CH Heating System Setting",
        translation_key="ch_heating_system_setting",
    ),
    SensorEntityDescription(
        key="Time_slot_type",
        name="Time Slot Type",
        translation_key="time_slot_type",
    ),
    SensorEntityDescription(
        key="Slot_current_CH",
        name="CH Slot Current",
        translation_key="ch_slot_current",
    ),
    SensorEntityDescription(
        key="Slot_current_DHW",
        name="DHW Slot Current",
        translation_key="dhw_slot_current",
    ),
    SensorEntityDescription(
        key="Heating_Curve",
        name="CH Heating Curve",
        translation_key="ch_heating_curve",
    ),
    SensorEntityDescription(
        key="Mode_Setting_DHW",
        name="DHW Mode Setting",
        translation_key="dhw_mode_setting",
    ),
    SensorEntityDescription(
        key="Mode_Setting_CH",
        name="CH Mode Setting",
        translation_key="ch_mode_setting",
    ),
    SensorEntityDescription(
        key="DHW_Function",
        name="DHW Function",
        translation_key="dhw_function",
    ),
    SensorEntityDescription(
        key="Max_NumBer_Of_Timeslots_CH",
        name="CH Max Timeslots",
        translation_key="ch_max_timeslots",
    ),
    SensorEntityDescription(
        key="Max_NumBer_Of_Timeslots_DHW",
        name="DHW Max Timeslots",
        translation_key="dhw_max_timeslots",
    ),
    SensorEntityDescription(
        key="reserved_data1",
        name="CH Water Pressure",
        translation_key="ch_water_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        unit_of_measurement=UnitOfPressure.BAR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="reserved_data2",
        name="Reserved data2",
        translation_key="reserved_data2",
    ),
    SensorEntityDescription(
        key="reserved_data3",
        name="Reserved data3",
        translation_key="reserved_data3",
    ),
    SensorEntityDescription(
        key="Fault_List",
        name="Fault List",
        translation_key="fault_list",
    ),
    SensorEntityDescription(
        key="Maintenance",
        name="Maintenance",
        translation_key="maintenance",
    ),
    SensorEntityDescription(
        key="Brand",
        name="Brand",
        translation_key="brand",
    ),
    SensorEntityDescription(
        key="DSN",
        name="DSN",
        translation_key="dsn",
    ),
    SensorEntityDescription(
        key="WarmStar_Tank_Loading_Enable",
        name="WarmStar_Tank_Loading_Enable",
        translation_key="warmstar_tank_loading_enable",
    ),
    # SensorEntityDescription(
    #     key="Start_Time_DHW1",
    #     name="DHW Time1 Monday",
    #     translation_key="dhw_start_time1",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_DHW2",
    #     name="DHW Time2 Tuesday",
    #     translation_key="dhw_start_time2",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_DHW3",
    #     name="DHW Time3 Wednesday",
    #     translation_key="dhw_start_time3",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_DHW4",
    #     name="DHW Time4 Thursday",
    #     translation_key="dhw_start_time4",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_DHW5",
    #     name="DHW Time5 Friday",
    #     translation_key="dhw_start_time5",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_DHW6",
    #     name="DHW Time6 Saturday",
    #     translation_key="dhw_start_time6",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_DHW7",
    #     name="DHW Time7 Sunday",
    #     translation_key="dhw_start_time7",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_CH1",
    #     name="CH Time1 Monday",
    #     translation_key="ch_start_time1",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_CH2",
    #     name="CH Time2 Tuesday",
    #     translation_key="ch_start_time2",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_CH3",
    #     name="CH Time3 Wednesday",
    #     translation_key="ch_start_time3",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_CH4",
    #     name="CH Time4 Thursday",
    #     translation_key="ch_start_time4",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_CH5",
    #     name="CH Time5 Friday",
    #     translation_key="ch_start_time5",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_CH6",
    #     name="CH Time6 Saturday",
    #     translation_key="ch_start_time6",
    # ),
    # SensorEntityDescription(
    #     key="Start_Time_CH7",
    #     name="CH Time7 Sunday",
    #     translation_key="ch_start_time7",
    # ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    """Set up Vaillant sensors."""
    device_id = entry.data.get(CONF_DID)
    client: VaillantClient = hass.data[DOMAIN][API_CLIENT][entry.entry_id]

    added_entities = []

    @callback
    def async_new_entities(device_attrs: dict[str, Any]):
        _LOGGER.debug("add vaillant sensor entities. device attrs: %s", device_attrs)
        new_entities = []
        for description in SENSOR_DESCRIPTIONS:
            if (
                description.key in device_attrs
                and description.key not in added_entities
            ):
                new_entities.append(VaillantSensorEntity(client, description))
                added_entities.append(description.key)

        if len(new_entities) > 0:
            async_add_entities(new_entities)

    unsub = async_dispatcher_connect(
        hass, EVT_DEVICE_CONNECTED.format(device_id), async_new_entities
    )

    hass.data[DOMAIN][DISPATCHERS][device_id].append(unsub)

    return True


class VaillantSensorEntity(VaillantEntity, SensorEntity):
    """Define a Vaillant sensor entity."""

    def __init__(
        self,
        client: VaillantClient,
        description: SensorEntityDescription,
    ):
        super().__init__(client)
        self.entity_description = description
        # set native_unit_of_measurement
        self._attr_native_unit_of_measurement = description.unit_of_measurement

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return f"{self.device.id}_{self.entity_description.key}"

    @callback
    def update_from_latest_data(self, data: dict[str, Any]) -> None:
        """Update the entity from the latest data."""

        value = data.get(self.entity_description.key)
        # 处理 Tank_temperature，可能为华氏度，直接转换为摄氏度
        if self.entity_description.key == "Tank_temperature" and value is not None:
            value = (value - 32) * 5 / 9

        # 处理 水压，十六进制转换为Bar
        if self.entity_description.key == "reserved_data1" and value is not None:
            value = int(value, 16) / 10.0

        # 以下功能已使用text entity: text.py 替代，实现修改和控制定时功能
        #
        # # 处理以 Start_Time_ 开头的传感器
        # if self.entity_description.key.startswith("Start_Time_") and value is not None:
        #     # 确保 value 是字符串且长度为 24
        #     if isinstance(value, str) and len(value) == 24:
        #         # 分割为三组定时器，每组 8 字符
        #         slots = [value[i:i+8] for i in range(0, 24, 8)]
        #         formatted_times = []

        #         for slot in slots:
        #             # 如果整组为 00000000，跳过
        #             if slot == "00000000":
        #                 continue
        #             # 解析开始和结束时间
        #             start_hour = int(slot[0:2], 16)
        #             start_minute = int(slot[2:4], 16)
        #             end_hour = int(slot[4:6], 16)
        #             end_minute = int(slot[6:8], 16)
        #             # 格式化为 HH:MM-HH:MM
        #             formatted_time = f"{start_hour:02d}:{start_minute:02d}-{end_hour:02d}:{end_minute:02d}"
        #             formatted_times.append(formatted_time)

        #         # 根据非零组数设置输出
        #         if not formatted_times:
        #             value = "0"
        #         else:
        #             value = ", ".join(formatted_times)
        #     else:
        #         _LOGGER.warning(
        #             "Invalid Start_Time format for %s: %s",
        #             self.entity_description.key,
        #             value
        #         )
        #         value = None

        self._attr_native_value = value
        self._attr_available = value is not None
