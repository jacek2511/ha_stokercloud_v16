import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from stokercloud_v16.client import StokerCloudClientV16

_LOGGER = logging.getLogger(__name__)

class StokerCloudV16ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            
            client = StokerCloudClientV16(
                user_input[CONF_USERNAME], 
                user_input[CONF_PASSWORD], 
                session
            )
            
            try:
                await client.fetch_data()
                return self.async_create_entry(
                    title=f"Kocioł: {user_input[CONF_USERNAME]}", 
                    data=user_input
                )
            except Exception as e:
                _LOGGER.error("Szczegóły błędu w ConfigFlow: %s", str(e) or type(e).__name__)
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )
