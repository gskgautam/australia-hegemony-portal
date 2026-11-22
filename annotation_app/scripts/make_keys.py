#!/usr/bin/env python3
"""
Create annotation_app/accounts/apikeys.json on the server.

Asks for the admin password, the annotator sign-up access code and the
OpenRouter API key (input is hidden), stores only hashes of the two
passwords, and generates a random Flask secret key. Nothing is printed.

    python annotation_app/scripts/make_keys.py
"""

import getpass
import json
import os
import secrets
import sys

from werkzeug.security import generate_password_hash

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS_PATH = os.path.join(APP_DIR, "accounts", "apikeys.json")


def ask(prompt, min_length=1):
    while True:
        value = getpass.getpass(prompt).strip()
        if len(value) >= min_length:
            return value
        print(f"  Please enter at least {min_length} characters.")


def ask_twice(prompt, min_length):
    while True:
        first = ask(prompt, min_length)
        if ask("  Type it again: ", 1) == first:
            return first
        print("  They didn't match. Try again.")


def main():
    if os.path.exists(KEYS_PATH):
        answer = input(f"{KEYS_PATH} already exists. Replace it? [y/N] ").strip().lower()
        if answer != "y":
            print("Left unchanged.")
            return 1

    admin_username = input("Admin username [admin]: ").strip() or "admin"
    admin_password = ask_twice("Admin password (hidden, 10+ characters): ", 10)
    access_code = ask_twice("Annotator sign-up access code (hidden, 8+ characters): ", 8)
    openrouter_key = ask("OpenRouter API key (hidden): ", 20)
    if not openrouter_key.startswith("sk-or-"):
        print("  Warning: OpenRouter keys usually start with 'sk-or-'. Saving anyway.")

    keys = {
        "FLASK_SECRET_KEY": secrets.token_hex(32),
        "OPENROUTER_API_KEY": openrouter_key,
        "ADMIN_USERNAME": admin_username,
        "ADMIN_PASSWORD_HASH": generate_password_hash(admin_password),
        "ANNOTATOR_PASSWORD_HASH": generate_password_hash(access_code),
    }

    os.makedirs(os.path.dirname(KEYS_PATH), exist_ok=True)
    with open(KEYS_PATH, "w") as f:
        json.dump(keys, f, indent=2)
    os.chmod(KEYS_PATH, 0o600)
    print(f"Saved {KEYS_PATH} (readable only by you).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
