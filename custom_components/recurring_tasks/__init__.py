from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent
import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    tasks = config[DOMAIN]['tasks']
    hass.data[DOMAIN] = tasks

    for task in tasks:
        hass.helpers.discovery.load_platform('binary_sensor', DOMAIN, task, config)

    def handle_mark_done(call):
        task_name = call.data.get('name')
        for entity in hass.data[DOMAIN].values():
            if entity.name == f"binary_sensor.recurring_{task_name}":
                entity.mark_done()
                break

    hass.services.register(DOMAIN, 'mark_done', handle_mark_done)

    def handle_notification_action(event):
        action = event.data.get('action')
        if action.startswith('RECURRING_TASKS_'):
            task_action = action.split('__')[1].lower()
            task_name = action.split('__')[2].lower()
            # Find the corresponding sensor
            for entity in hass.data[DOMAIN].values():
                if entity.name == f"binary_sensor.recurring_{task_name}":
                    if task_action == 'mark_done':
                        entity.mark_done()
                    elif task_action in ['tomorrow', 'saturday']:
                        entity.reschedule(task_action)
                    break

    hass.bus.listen('mobile_app_notification_action', handle_notification_action)

    return True


