"""
Reads vehicle status from BMW connected drive portal.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.bmw_connected_drive/
"""
import asyncio
import logging

from custom_components.bmw_connected_drive import DOMAIN as BMW_DOMAIN
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level

DEPENDENCIES = ['bmw_connected_drive']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the BMW sensors."""
    accounts = hass.data[BMW_DOMAIN]
    _LOGGER.debug('Found BMW accounts: %s',
                  ', '.join([a.name for a in accounts]))
    devices = []
    for account in accounts:
        for vehicle in account.account.vehicles:
            for attribute_name in vehicle.drive_train_attributes:  
                device = BMWConnectedDriveSensor(account, vehicle,
                                                 attribute_name)
                devices.append(device)
            device = BMWConnectedDriveSensor(account, vehicle, 'mileage')
            devices.append(device)
    add_devices(devices, True)


class BMWConnectedDriveSensor(Entity):
    """Representation of a BMW vehicle sensor."""

    def __init__(self, account, vehicle, attribute: str):
        """Constructor."""
        self._vehicle = vehicle
        self._account = account
        self._attribute = attribute
        self._state = None
        self._unit_of_measurement = None
        self._name = '{} {}'.format(self._vehicle.name, self._attribute)
        self._unique_id = '{}-{}'.format(self._vehicle.vin, self._attribute)

    @property
    def should_poll(self) -> bool:
        """Data update is triggered from BMWConnectedDriveEntity."""
        return False

    @property
    def unique_id(self):
        """Return the unique ID of the binary sensor."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        # pylint: disable=import-error
        from bimmer_connected.state import ChargingState
        vehicle_state = self._vehicle.state
        charge_state = vehicle_state.charging_status in \
                          [ChargingState.CHARGING]

        if self._attribute == 'mileage':
            return 'mdi:speedometer'
        elif self._attribute in (
            'remaining_range_total', 'remaining_range_electric',
            'remaining_range_fuel', 'max_range_electric'):
            return 'mdi:ruler'
        elif self._attribute == 'remaining_fuel':
            return 'mdi:gas-station'
        elif self._attribute == 'charging_time_remaining':
            return 'mdi:update'
        elif self._attribute == 'charging_status':
            return 'mdi:battery-charging'
        elif self._attribute == 'charging_level_hv':
            return icon_for_battery_level(
                battery_level=vehicle_state.charging_level_hv,
                charging=charge_state)

    @property
    def state(self):
        """Return the state of the sensor.

        The return type of this call depends on the attribute that
        is configured.
        """
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Get the unit of measurement."""
        if self._attribute in (
            'mileage', 'remaining_range_total', 'remaining_range_electric',
            'remaining_range_fuel', 'max_range_electric'):
            return 'km'
        elif self._attribute == 'remaining_fuel':
            return 'l'
        elif self._attribute == 'charging_time_remaining':
            return 'h'
        elif self._attribute == 'charging_level_hv':
            return '%'
        else:
            self._unit_of_measurement = None

    @property
    def device_state_attributes(self):
        """Return the state attributes of the binary sensor."""
        return {
            'last_update': self._vehicle.state.timestamp.replace(tzinfo=None),
            'car': self._vehicle.name
        }

    def update(self) -> None:
        """Read new state data from the library."""
        _LOGGER.debug('Updating %s', self._vehicle.name)
        vehicle_state = self._vehicle.state
        if self._attribute == 'charging_status':
            self._state = getattr(vehicle_state, self._attribute.value)
        else:
            self._state = getattr(vehicle_state, self._attribute)

    def update_callback(self):
        """Schedule a state update."""
        self.schedule_update_ha_state(True)

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Add callback after being added to hass.
        
        Show latest data after startup.
        """
        self._account.add_update_listener(self.update_callback)
