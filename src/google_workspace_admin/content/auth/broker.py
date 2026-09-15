"""Internal Content authorization broker; no token acquisition occurs here."""

from __future__ import annotations

"""Reserved for the startup-owned Content authorization composition.

The production package deliberately contains no public broker factory.  The
bootstrap assembles the broker closure together with the profile/subject
policy, so runtime inputs cannot replace or invoke an alternate broker.
"""
