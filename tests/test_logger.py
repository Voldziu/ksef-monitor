from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock


def _make_settings(tmp_path: Path, *, to_file: bool = False):
    s = MagicMock()
    s.LOG_LEVEL = "DEBUG"
    s.LOG_FORMAT = "text"
    s.LOG_DIR = tmp_path / "logs"
    s.LOG_FILE_NAME = "app.log"
    s.LOG_MAX_BYTES = 1024 * 1024
    s.LOG_BACKUP_COUNT = 2
    s.LOG_TO_CONSOLE = True
    s.LOG_TO_FILE = to_file
    return s


def test_setup_logging_adds_handlers(tmp_path: Path):
    import importlib
    import app.utils.logger as log_mod
    importlib.reload(log_mod)

    settings = _make_settings(tmp_path)
    log_mod.setup_logging(settings)

    app_logger = logging.getLogger("app")
    assert len(app_logger.handlers) >= 1


def test_setup_logging_idempotent(tmp_path: Path):
    import importlib
    import app.utils.logger as log_mod
    importlib.reload(log_mod)

    settings = _make_settings(tmp_path)
    log_mod.setup_logging(settings)
    handler_count = len(logging.getLogger("app").handlers)
    log_mod.setup_logging(settings)
    assert len(logging.getLogger("app").handlers) == handler_count


def test_get_logger_child_inherits_config(tmp_path: Path):
    import importlib
    import app.utils.logger as log_mod
    importlib.reload(log_mod)

    settings = _make_settings(tmp_path)
    log_mod.setup_logging(settings)

    child = log_mod.get_logger("app.test_module")
    # Child logger propagates to "app" logger which has our handlers.
    # Verify the child's effective level comes from the parent.
    assert child.getEffectiveLevel() == logging.DEBUG
    assert child.parent is logging.getLogger("app")


def test_file_handlers_created(tmp_path: Path):
    import importlib
    import app.utils.logger as log_mod
    importlib.reload(log_mod)

    settings = _make_settings(tmp_path, to_file=True)
    log_mod.setup_logging(settings)

    handlers = logging.getLogger("app").handlers
    file_handlers = [h for h in handlers if hasattr(h, "baseFilename")]
    assert len(file_handlers) == 2
