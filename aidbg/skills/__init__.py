"""aidbg skills — debug knowledge as auto-discovered plugins.

Modules here are imported automatically by aidbg.core.registry.discover(); each
calls @register. There is intentionally NO explicit import list — dropping a new
skill file into this package (or a directory on AIDBG_SKILLS_PATH) is enough.

Skills depend only on the aidbg.core API and reach the design/TB source solely
through the read-only Context.
"""
