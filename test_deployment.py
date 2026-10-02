# SPDX-License-Identifier: CC-BY-NC-SA-4.0
import asyncio
import importlib
import unittest
from pkgutil import iter_modules
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import erm

from datamodels.ShiftManagement import ShiftManagement
from datamodels.Warnings import Warnings
from erm import Bot


class CommandRegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = Bot(command_prefix="!", intents=discord.Intents.none())
        self.bot.tree.sync = AsyncMock(return_value=[])
        self.bot.tree.copy_global_to = MagicMock()

    async def test_registers_global_commands_once(self):
        with patch.dict("os.environ", {"SYNC_COMMANDS": "TRUE", "COMMAND_GUILD_ID": "0"}):
            await self.bot.sync_application_commands()
            await self.bot.sync_application_commands()
        self.bot.tree.sync.assert_awaited_once_with()
        self.bot.tree.copy_global_to.assert_not_called()

    async def test_registers_only_the_configured_test_guild(self):
        with patch.dict("os.environ", {"SYNC_COMMANDS": "TRUE", "COMMAND_GUILD_ID": "123456789012345678"}):
            await self.bot.sync_application_commands()
        guild = self.bot.tree.sync.call_args.kwargs["guild"]
        self.assertEqual(guild.id, 123456789012345678)
        self.bot.tree.copy_global_to.assert_called_once_with(guild=guild)

    async def test_sync_can_be_disabled(self):
        with patch.dict("os.environ", {"SYNC_COMMANDS": "FALSE"}):
            await self.bot.sync_application_commands()
        self.bot.tree.sync.assert_not_called()

    async def test_failed_sync_can_be_retried(self):
        self.bot.tree.sync.side_effect = RuntimeError("Discord unavailable")
        with patch.dict("os.environ", {"SYNC_COMMANDS": "TRUE", "COMMAND_GUILD_ID": "0"}):
            with self.assertRaises(RuntimeError):
                await self.bot.sync_application_commands()
        self.assertFalse(self.bot.is_synced)

    async def test_owner_is_the_discord_application_owner(self):
        self.bot.application_info = AsyncMock(return_value=SimpleNamespace(
            team=None, owner=SimpleNamespace(id=123456789012345678)
        ))
        self.assertFalse(await self.bot.is_owner(SimpleNamespace(id=1394817794427846737)))
        self.assertTrue(await self.bot.is_owner(SimpleNamespace(id=123456789012345678)))


class StandaloneDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_shift_start_works_without_legacy_api_variables(self):
        collection = SimpleNamespace(insert_one=AsyncMock())
        shifts = ShiftManagement({"shift_management": collection}, "shift_management")
        member = SimpleNamespace(id=123456789012345678, name="Fable test", display_name="Fable test")
        with patch.dict("os.environ", {}, clear=True):
            identifier = await shifts.add_shift_by_user(member, "Default", [], 987654321012345678)
        document = collection.insert_one.call_args.args[0]
        self.assertEqual(document["_id"], identifier)
        self.assertEqual(document["UserID"], member.id)

    async def test_punishment_delete_works_without_legacy_api_variables(self):
        collection = SimpleNamespace(
            find_one=AsyncMock(return_value={"_id": "fixture", "Guild": 42}),
            delete_one=AsyncMock(return_value="deleted")
        )
        warnings = Warnings(SimpleNamespace(db={"punishments": collection, "recovery": MagicMock()}))
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(await warnings.remove_warning_by_snowflake(77, 42), "deleted")
        collection.delete_one.assert_awaited_once_with({"Snowflake": 77})


class StartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_standalone_startup_loads_commands_without_legacy_api(self):
        bot = Bot(command_prefix="!", intents=discord.Intents.none())
        bot._connection.user = SimpleNamespace(name="Fable fixture")
        bot.application_info = AsyncMock(return_value=SimpleNamespace(
            install_params=None, custom_install_url=None
        ))
        bot.tree.sync = AsyncMock(return_value=[])
        mongo = MagicMock()
        mongo.admin.command = AsyncMock()
        mongo.__getitem__.return_value.__getitem__.return_value.find.return_value.__aiter__.return_value = []
        with (
            patch.object(erm, "bot", bot),
            patch("erm.AsyncMongoClient", return_value=mongo),
            patch("erm.EmojiController.prefetch_emojis", new_callable=AsyncMock),
            patch("erm.start_tasks", new_callable=AsyncMock),
            patch("discord.ext.tasks.Loop.start"),
            patch.dict("os.environ", {
                "INTERNAL_API_ENABLED": "FALSE", "SYNC_COMMANDS": "TRUE", "COMMAND_GUILD_ID": "0"
            })
        ):
            try:
                await bot.setup_hook()
                await asyncio.sleep(0)
                self.assertTrue(bot.setup_status)
                self.assertIsNotNone(bot.tree.get_command("setup"))
                self.assertNotIn("utils.api", bot.extensions)
                bot.tree.sync.assert_awaited_once_with()
                mongo.admin.command.assert_awaited_once_with("ping")
            finally:
                for session in bot.external_http_sessions:
                    await session.close()
                for name in list(bot.extensions):
                    await bot.unload_extension(name)


class ExtensionImportTests(unittest.TestCase):
    def test_all_extensions_import_with_production_dependencies(self):
        for directory in ("cogs", "events", "tasks"):
            for module in iter_modules([directory], directory + "."):
                with self.subTest(module=module.name):
                    importlib.import_module(module.name)
