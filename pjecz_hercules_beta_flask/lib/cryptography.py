"""
Cryptography
"""

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def convert_string_to_fernet_key(input_string: str, salt: str) -> bytes:
    """Converts a string to a Fernet compatible encryption key"""
    input_string_bytes = input_string.encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # Fernet requires 32 raw bytes for its key material
        salt=salt.encode("utf-8"),  # Salt for the Key Derivation Function
        iterations=600000,  # OWASP recommendation (as of early 2024)
        backend=default_backend(),
    )
    derived_key_bytes = kdf.derive(input_string_bytes)
    return base64.urlsafe_b64encode(derived_key_bytes)


def simmetric_crypt(input_str: str, fernet_key: str) -> str:
    """Cifrar"""
    fernet = Fernet(fernet_key)
    input_bytes = input_str.encode("utf-8")
    encrypted_input_bytes = fernet.encrypt(input_bytes)
    return encrypted_input_bytes.decode("utf-8")


def simmetric_decrypt(input_str: str, fernet_key: str) -> str:
    """Descifrar"""
    fernet = Fernet(fernet_key)
    input_bytes = input_str.encode("utf-8")
    try:
        decrypted_email_bytes = fernet.decrypt(input_bytes)
        return decrypted_email_bytes.decode("utf-8")
    except InvalidToken:
        raise ValueError("La clave de cifrado no es válida o el texto cifrado ha sido modificado.")
