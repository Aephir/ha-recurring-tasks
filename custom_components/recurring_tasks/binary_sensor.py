from homeassistant.components.binary_sensor import BinarySensorEntity
from datetime import datetime, timedelta
import homeassistant.util.dt as dt_util


class RecurringTaskSensor(BinarySensorEntity):
    def __init__(self, hass, name, interval):
        self.hass = hass
        self._name = name
        self._state = False
        self._last_done = None
        self._next_due_date = None
        self._interval = interval

    @property
    def name(self):
        return f"recurring_{self._name}"

    @property
    def is_on(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return {
            "last_done": self._last_done,
            "next_due_date": self._next_due_date
        }

    def update(self):
        today = dt_util.now().date()
        if self._next_due_date and today >= self._next_due_date:
            self._state = True
        else:
            self._state = False

    # Additional methods for handling state changes
