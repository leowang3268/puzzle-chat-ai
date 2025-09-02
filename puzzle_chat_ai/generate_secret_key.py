#!/usr/bin/env python3
"""
Generate a secure Django secret key for production use.
Run this script and copy the output to your .env file.
"""

import secrets
import string

def generate_secret_key(length=50):
    """Generate a secure Django secret key."""
    characters = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return ''.join(secrets.choice(characters) for _ in range(length))

if __name__ == "__main__":
    secret_key = generate_secret_key()
    print("Generated Django Secret Key:")
    print(f"SECRET_KEY={secret_key}")
    print("\nCopy the line above to your .env file.")