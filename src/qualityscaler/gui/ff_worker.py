# Compatibility shim — module moved to qualityscaler.app (issue #65 phase 1); removed in phase 5.
from qualityscaler.app.workers.framegen import *  # noqa: F401,F403
from qualityscaler.app.workers.framegen import _frame_generation_process_main  # noqa: F401
