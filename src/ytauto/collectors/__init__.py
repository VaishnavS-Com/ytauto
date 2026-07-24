"""Collectors — modules that discover topic ideas from the outside world.

Each collector follows the same contract:

    collect() -> list[dict]   where each dict has keys: title, source

The pipeline doesn't care HOW ideas were found (RSS, Reddit, trends...).
Adding a new source later = adding one file that honors the contract.
That uniform contract is what makes the system modular.

DESIGN RULE: fetch (network) and parse (pure logic) are SEPARATE functions.
Parsing pure text/dicts means tests can feed in saved sample data and never
touch the network — fast, reliable tests.
"""
