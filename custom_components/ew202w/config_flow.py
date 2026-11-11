"""EW202W config flow."""
from __future__ import annotations
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_PORT, DEFAULT_PORT, DOMAIN


class EW202WConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # Tek sunucu örneği yeterli (birden çok lamba aynı porta bağlanır)
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="EW202W Uyku Işığı", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            }),
        )
