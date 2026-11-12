"""EW202W config flow."""
from __future__ import annotations
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (ConfigEntry, ConfigFlow, ConfigFlowResult,
                                          OptionsFlow)
from homeassistant.core import callback
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .const import CONF_PORT, CONF_SOUND_NAMES, DEFAULT_PORT, DOMAIN


class EW202WConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return EW202WOptionsFlow()

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


class EW202WOptionsFlow(OptionsFlow):
    """Lambaya özel ses adları (ör. değiştirilmiş bir MP3'e 'Beyaz Gürültü' adı vermek)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SOUND_NAMES, "")
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_SOUND_NAMES, description={"suggested_value": current}):
                    TextSelector(TextSelectorConfig(multiline=True)),
            }),
        )
