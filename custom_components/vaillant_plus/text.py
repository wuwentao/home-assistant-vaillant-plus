"""Vaillant weekly start-time control (Text entities).

Provides 7 TextEntity entities: Start_Time_CH1 ... Start_Time_CH7.
User writes values like "07:00-09:00, 18:00-22:00" (up to 3 slots).
The code encodes/decodes to/from the device 24-character hex format
(each slot = 8 hex chars; "00000000" means unused slot).
"""
from __future__ import annotations

import logging
from typing import Any, List, Tuple

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import VaillantClient
from .const import CONF_DID, DISPATCHERS, DOMAIN, EVT_DEVICE_CONNECTED, API_CLIENT
from .entity import VaillantEntity

_LOGGER = logging.getLogger(__name__)

# Keys and friendly names for CH Start Times (Mon..Sun)
CH_START_KEYS = [
    ("Start_Time_CH1", "CH Start Time 1"),
    ("Start_Time_CH2", "CH Start Time 2"),
    ("Start_Time_CH3", "CH Start Time 3"),
    ("Start_Time_CH4", "CH Start Time 4"),
    ("Start_Time_CH5", "CH Start Time 5"),
    ("Start_Time_CH6", "CH Start Time 6"),
    ("Start_Time_CH7", "CH Start Time 7"),
]


def encode_timeslots_from_list(slots: List[Tuple[int, int, int, int]]) -> str:
    """Encode up to 3 slots into a 24-char hex string.
    slots: list of (start_h, start_m, end_h, end_m)
    Unused slots -> "00000000".
    """
    parts: List[str] = []
    for i in range(3):
        if i < len(slots):
            sh, sm, eh, em = slots[i]
            # clamp values
            sh = max(0, min(23, int(sh)))
            eh = max(0, min(23, int(eh)))
            sm = max(0, min(59, int(sm)))
            em = max(0, min(59, int(em)))
            parts.append(f"{sh:02X}{sm:02X}{eh:02X}{em:02X}")
        else:
            parts.append("00000000")
    return "".join(parts)


def parse_display_string_to_slots(display: str) -> List[Tuple[int, int, int, int]]:
    """Parse a display string like '07:00-09:00, 18:00-22:00' into list of tuples.
    Returns up to 3 tuples. If display is '0' or empty -> empty list.
    Raises ValueError on malformed input.
    """
    if display is None:
        return []
    s = display.strip()
    if s == "" or s == "0" or s.lower() in ("none", "null"):
        return []

    parts = [p.strip() for p in s.split(",") if p.strip()]
    slots: List[Tuple[int, int, int, int]] = []
    for p in parts[:3]:
        if "-" not in p:
            raise ValueError(f"invalid timeslot (missing '-'): {p}")
        start, end = p.split("-", 1)
        if ":" not in start or ":" not in end:
            raise ValueError(f"invalid time format (missing ':'): {p}")
        sh_str, sm_str = start.split(":", 1)
        eh_str, em_str = end.split(":", 1)
        sh = int(sh_str)
        sm = int(sm_str)
        eh = int(eh_str)
        em = int(em_str)
        if not (0 <= sh <= 23 and 0 <= eh <= 23 and 0 <= sm <= 59 and 0 <= em <= 59):
            raise ValueError(f"time values out of range: {p}")
        slots.append((sh, sm, eh, em))
    return slots


class VaillantTimeTextEntity(VaillantEntity, TextEntity):
    """Writable text entity representing a Start_Time_CHn."""

    def __init__(self, client: VaillantClient, key: str, name: str):
        super().__init__(client)
        self._key = key
        self._attr_name = name
        self._attr_native_value: str | None = None
        # available will be set when update_from_latest_data runs

    @property
    def unique_id(self) -> str | None:
        return f"{self.device.id}_{self._key}"

    @callback
    def update_from_latest_data(self, data: dict[str, Any]) -> None:
        """Update display value from device data (24-char hex -> readable text)."""
        val = data.get(self._key)
        if isinstance(val, str) and len(val) == 24:
            slots = [val[i : i + 8] for i in range(0, 24, 8)]
            formatted_times: List[str] = []
            for slot in slots:
                if slot == "00000000":
                    continue
                try:
                    sh = int(slot[0:2], 16)
                    sm = int(slot[2:4], 16)
                    eh = int(slot[4:6], 16)
                    em = int(slot[6:8], 16)
                    formatted_times.append(f"{sh:02d}:{sm:02d}-{eh:02d}:{em:02d}")
                except Exception as exc:
                    _LOGGER.warning("Failed to parse timeslot %s for %s: %s", slot, self._key, exc)
                    continue
            self._attr_native_value = ", ".join(formatted_times) if formatted_times else "0"
            self._attr_available = True
        else:
            # if device didn't provide the key or invalid format
            self._attr_native_value = None
            self._attr_available = False

    async def async_set_value(self, value: str) -> None:
        """Called when the user sets the Text entity in the UI.

        Accepts:
          - "0" to clear all slots
          - "HH:MM-HH:MM, ..." up to 3 segments
        """
        _LOGGER.debug("User requested set %s -> %s", self._key, value)
        # allow the special clear token
        if value is None:
            _LOGGER.error("No value provided to set for %s", self._key)
            return

        display = value.strip()
        try:
            if display == "0" or display == "":
                slots: List[Tuple[int, int, int, int]] = []
            else:
                slots = parse_display_string_to_slots(display)
        except ValueError as exc:
            _LOGGER.error("Invalid time format provided for %s: %s", self._key, exc)
            return

        hexstr = encode_timeslots_from_list(slots)
        _LOGGER.debug("Encoded %s -> %s", slots, hexstr)

        try:
            # Use same control_device API shape as in climate.py
            resp = await self._client.control_device({self._key: hexstr})
        except Exception as exc:
            _LOGGER.error("Exception when sending control for %s: %s", self._key, exc)
            resp = None

        # attempt to determine success: if client returns truthy or None (some clients may not return),
        # we'll optimistically update local state. If client explicitly returns False, log error.
        if resp is False:
            _LOGGER.error("Device rejected update for %s -> %s", self._key, hexstr)
            return

        # update local displayed value to reflect what we sent
        if slots:
            self._attr_native_value = ", ".join(f"{s[0]:02d}:{s[1]:02d}-{s[2]:02d}:{s[3]:02d}" for s in slots)
        else:
            self._attr_native_value = "0"

        self._attr_available = True
        # push to HA state machine
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    """Set up Vaillant Start_Time_CH Text entities from a config entry."""
    device_id = entry.data.get(CONF_DID)
    client: VaillantClient = hass.data[DOMAIN][API_CLIENT][entry.entry_id]

    added_keys: List[str] = []

    @callback
    def async_new_time_entities(device_attrs: dict[str, Any]):
        _LOGGER.debug("add vaillant time entities. device attrs keys: %s", list(device_attrs.keys()))
        new_entities: List[VaillantTimeTextEntity] = []
        for key, friendly_name in CH_START_KEYS:
            if key in device_attrs and key not in added_keys:
                new_entities.append(VaillantTimeTextEntity(client, key, friendly_name))
                added_keys.append(key)

        if new_entities:
            async_add_entities(new_entities)

    unsub = async_dispatcher_connect(hass, EVT_DEVICE_CONNECTED.format(device_id), async_new_time_entities)
    hass.data[DOMAIN][DISPATCHERS][device_id].append(unsub)

    return True