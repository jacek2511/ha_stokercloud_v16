import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from stokercloud_v16.client import StokerCloudClientV16

class StokerCloudV16ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            session = self.hass.helpers.aiohttp_client.async_get_clientsession()
            client = StokerCloudClientV16(
                user_input[CONF_USERNAME], 
                user_input[CONF_PASSWORD], 
                session
            )
            
            try:
                await client.fetch_data() # Test logowania i pobrania danych
                return self.async_create_entry(
                    title=f"Kocioł: {user_input[CONF_USERNAME]}", 
                    data=user_input
                )
            except Exception:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )
