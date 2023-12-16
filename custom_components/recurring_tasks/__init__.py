from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent
import logging
from const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Recurring Tasks component."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    hass.data[DOMAIN] = {}

    # Load binary_sensor platform
    hass.async_create_task(
        hass.helpers.discovery.async_load_platform('binary_sensor', DOMAIN, {}, config)
    )

    return True
