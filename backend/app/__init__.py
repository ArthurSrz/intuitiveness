"""FastAPI backend for the intuitiveness descent–ascent engine (spec 017 Phase A).

Thin, STATELESS HTTP layer over the headless `intuitiveness` core: every request
loads the session from the durable store, runs one engine transition through
`NavigationSession`, and saves the updated tree back. No business logic lives
here — it is pure HTTP ↔ engine adaptation.
"""
