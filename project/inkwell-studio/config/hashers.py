import os

from django.contrib.auth.hashers import PBKDF2PasswordHasher


class CustomPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    """PBKDF2 hasher whose iteration count is driven by the PBKDF2_ITERATIONS env var.

    Django's built-in PBKDF2PasswordHasher hard-codes ``iterations`` as a
    class-level attribute, so a ``PBKDF2_ITERATIONS`` Django setting has no
    effect.  This subclass reads the env var directly so the value configured
    in ``.env`` / ``settings/base.py`` actually changes the number of rounds
    used when hashing new passwords.
    """

    iterations = int(os.getenv("PBKDF2_ITERATIONS", "600000"))
