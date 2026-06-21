"""aidbg skills — debug knowledge as plugins.

Importing this package registers every skill (each module calls @register).
Skills depend only on the `aidbg.core` API; they never touch infra internals
or the design/TB source except through the read-only Context.
"""
from . import glitch_triage, reg_data_mismatch, tranif_contention, uvm_env  # noqa: F401
