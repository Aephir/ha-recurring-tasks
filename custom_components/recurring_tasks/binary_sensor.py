import logging
from datetime import datetime, timedelta
import homeassistant.util.dt as dt_util
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change, async_call_later
from homeassistant.const import (
    STATE_HOME
)
from .const import (
    DOMAIN
)

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass: HomeAssistant, config, add_entities, discovery_info=None):
    if discovery_info is None:
        return

    sensors = []
    for task_name, task_info in hass.data[DOMAIN].items():
        sensor = RecurringTaskSensor(hass, task_name, task_info)
        sensors.append(sensor)

    add_entities(sensors)


class RecurringTaskSensor(BinarySensorEntity):
    def __init__(self, hass, name, task_info):
        self.hass = hass
        self._name = name
        self._task_info = task_info
        self._state = False
        self._last_done = task_info.get("last_done")
        self._next_due_date = task_info.get("next_due_date")
        self._interval = task_info.get("interval", 7)  # Default to 7 days
        self.listeners = []
        self.schedule_daily_update()

    def schedule_daily_update(self):
        """Schedule an update every day at a specific time (e.g., midnight)."""
        now = datetime.now()
        midnight = now.replace(hour=0, minute=3, second=16, microsecond=0) + timedelta(days=1)
        delay = (midnight - now).total_seconds()
        async_call_later(delay, self.trigger_update)

    def trigger_update(self, _):
        """Trigger the update method."""
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return f"binary_sensor.recurring_{self._name}"

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
            if not self._state:
                self._state = True
                self.start_listening()
        else:
            if self._state:
                self._state = False
                self.stop_listening()

    def start_listening(self):
        for person in self._task_info['people']:
            listener = async_track_state_change(self.hass, person['tracker'], self.handle_person_home)
            self.listeners.append(listener)

    def stop_listening(self):
        while self.listeners:
            listener = self.listeners.pop()
            listener()  # This cancels the listener

    @callback
    def handle_device_tracker_change(self, entity_id, old_state, new_state):
        if new_state.state == STATE_HOME and self._state:
            self.send_notification()

    @callback
    def send_notification(self):
        for person in self._task_info['people']:
            if self.hass.states.get(person['tracker']).state == STATE_HOME:
                service = f"notify.{person['notify']}"
                message = f"Reminder: '{self._name}' task is due."
                data = {
                    "message": message,
                    "data": {
                        "actions": [
                            {"action": f"RECURRING_TASKS__MARK_DONE__{self._task_info['name'].upper()}", "title": "Mark as Done", "icon": "mdi:check"},
                            {"action": f"RECURRING_TASKS__TOMORROW__{self._task_info['name'].upper()}", "title": "Later", "icon": "mdi:clock"},
                        ]
                    }
                }
                self.hass.services.call('notify', service, data, blocking=True)

    def mark_done(self):
        self._last_done = dt_util.now().date()
        self._next_due_date = self._last_done + timedelta(days=self._interval)
        self._state = False
        self.async_write_ha_state()

    def reschedule(self, schedule_type):
        if schedule_type == 'tomorrow':
            target_date = datetime.now() + timedelta(days=1)
        elif schedule_type == 'saturday':
            target_date = self.get_next_saturday()
        else:
            # Handle invalid schedule_type if necessary
            return

        target_time = target_date.replace(hour=10, minute=0, second=0, microsecond=0)
        async_call_later(self.hass, (target_time - datetime.now()).total_seconds(), self.check_and_send_notification)

    @staticmethod
    def get_next_saturday():
        today = datetime.now()
        days_ahead = 5 - today.weekday()  # Saturday is 5
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        next_saturday = today + timedelta(days=days_ahead)
        return next_saturday

    def check_and_send_notification(self, _):
        if any(self.hass.states.get(person['tracker']).state == STATE_HOME for person in self._task_info['people']):
            self.send_notification()

    def handle_person_home(self, entity_id, old_state, new_state):
        if new_state.state == STATE_HOME:
            self.send_notification()
            # Optionally, stop tracking state changes after the notification is sent
            # self.hass.helpers.event.async_track_state_change_cancel(self, entity_id, self.handle_person_home)

    # Additional methods as needed
