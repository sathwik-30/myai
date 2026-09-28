# Medha Personal Memory

This folder represents Medha's permanent memory about the authenticated owner.

Personal memory is owner-scoped and does not expire automatically.

Examples:
- owner preferences
- stable profile facts
- long-term projects
- learning preferences
- durable facts Medha explicitly learned about the owner

Runtime storage is kept in SQLite under backend/memory/data/medha_memory.db.
Do not place secrets, passwords, tokens, or credentials here.
