# -*- coding: utf-8 -*-
"""
Crypto tools using NaCL library.
"""
import json
import logging
import os
import uuid
from typing import Iterable, Union, Dict

import nacl.utils
from nacl.encoding import RawEncoder
from nacl.public import Box, PrivateKey, PublicKey
from nacl.secret import SecretBox
from nacl.signing import SigningKey, VerifyKey
from nacl.utils import EncryptedMessage

logger = logging.getLogger(__name__)

__author__ = "Robert Harder"
__email__ = "rob@iharder.net"


class AccountKeys:
    """Represents a user's public and private keys for both signing and encrypting.
    All four keys can be derived from a single SigningKey.
    If this object only represents public data, then provide a
    public signing key, aka VerifyKey in nacl language, and the encryption public key
    will be derived.

    The user_id field is optional but made available since it is commonly used
    in subsequent systems.
    """

    def __init__(self,
                 user_id: str = None,
                 private_signing_key: Union[SigningKey, bytes] = None,
                 public_signing_key: Union[VerifyKey, bytes] = None):
        """
        Create an AccountKeys object for signing and encrypting data.
        The user_id field is optional but made available since it is commonly used
        in subsequent systems. If this represents only publicly-available data
        then instead of a private signing key, provide a public signing key.
        The encryption keys are derived from the signing keys.
        :param user_id: Optional user id string, not really used internally
        :param private_signing_key: SigningKey from which all four keys can be derived
        :param public_signing_key: VerifyKey from which the public encryption key can be derived
        """

        self._user_id: str = user_id

        # Signing key can be provided as the master of everything
        self._private_signing_key: SigningKey = \
            private_signing_key if isinstance(private_signing_key, SigningKey) \
                else (SigningKey(private_signing_key) if private_signing_key else None)

        # Optionally this might be an object that only maintains public keys
        self._public_signing_key: VerifyKey = \
            self._private_signing_key.verify_key if self._private_signing_key \
                else public_signing_key if isinstance(public_signing_key, VerifyKey) \
                else (VerifyKey(public_signing_key) if public_signing_key else None)

    def __repr__(self):
        return (f"{self.__class__.__name__}(user_id={self._user_id}, "
                f"public_signing_key={self.public_signing_key.encode(RawEncoder).hex().upper()})")

    def __eq__(self, other):
        try:
            return (isinstance(other, self.__class__) and
                    self.user_id == other.user_id and
                    self.private_signing_key == other.private_signing_key and
                    self.public_signing_key == other.public_signing_key)
        except:
            return False

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def private_signing_key(self) -> SigningKey:
        return self._private_signing_key

    @property
    def private_signing_key_bytes(self) -> bytes:
        return bytes(self.private_signing_key) if self.private_signing_key else None

    @property
    def public_signing_key(self) -> VerifyKey:
        return self._public_signing_key

    @property
    def public_signing_key_bytes(self) -> bytes:
        return bytes(self.public_signing_key) if self.public_signing_key else None

    @property
    def private_encryption_key(self) -> PrivateKey:
        return self.private_signing_key.to_curve25519_private_key()

    @property
    def private_encryption_key_bytes(self):
        return bytes(self.private_encryption_key) if self.private_encryption_key else None

    @property
    def public_encryption_key(self) -> PublicKey:
        return self.public_signing_key.to_curve25519_public_key()

    @property
    def public_encryption_key_bytes(self):
        return bytes(self.public_encryption_key) if self.public_encryption_key else None

    def sign_blob(self, blob: bytes) -> bytes:
        """
        Signs a blob of data with the private signing key and returns
        the signature as bytes
        """
        return KeyUtility.sign_blob(blob, self.private_signing_key)

    def is_valid_signature(self, blob: bytes, signature: bytes) -> bool:
        """Verifies that the blob of data matches the given signature."""
        return KeyUtility.is_valid_signature(blob=blob,
                                             signature=signature,
                                             public_signing_key=self.public_signing_key)

    def authenticated_encrypt_blob(self,
                                   blob: bytes,
                                   receiver_public_encryption_key: Union[PublicKey, bytes]) -> EncryptedMessage:
        """Encrypts a blob of data to a given recipient and provides authentication
        of the sender as well.
        """
        return KeyUtility.authenticated_encrypt_blob(blob=blob,
                                                     sender_private_encryption_key=self.private_encryption_key,
                                                     receiver_public_encryption_key=receiver_public_encryption_key)

    def authenticated_decrypt_blob(self,
                                   blob: Union[EncryptedMessage, str, bytes],
                                   sender_public_encryption_key: Union[PublicKey, bytes]) -> bytes:
        """Verifies and decrypts an encrypted blob of data. Raises an exception if any
        part of the process fails."""
        return KeyUtility.authenticated_decrypt_blob(blob=blob,
                                                     receiver_private_encryption_key=self.private_encryption_key,
                                                     sender_public_encryption_key=sender_public_encryption_key)

    def to_json(self) -> Dict:
        record = {}
        if self.user_id:
            record['user_id'] = self.user_id
        if self.public_signing_key:
            record['public_signing_key'] = self.public_signing_key.encode(RawEncoder).hex().upper()
        if self.private_signing_key:
            record['private_signing_key'] = self.private_signing_key.encode(RawEncoder).hex().upper()
        return record

    @staticmethod
    def from_json(json_dict: Dict) -> "AccountKeys":
        user_id = json_dict.get("user_id")
        signing_priv_key_hex = json_dict.get("private_signing_key", json_dict.get('priv_key'))
        signing_pub_key_hex = json_dict.get("public_signing_key", json_dict.get('pub_key'))
        signing_priv_key = SigningKey(bytes.fromhex(signing_priv_key_hex)) if signing_priv_key_hex else None
        signing_pub_key = VerifyKey(bytes.fromhex(signing_pub_key_hex)) if signing_pub_key_hex else None
        return AccountKeys(
            user_id=user_id,
            private_signing_key=signing_priv_key,
            public_signing_key=signing_pub_key)


class KeyUtility:
    """Helper class for organizing key utility functions - intended to expose
    things that will be helpful for derivative app developers."""

    @staticmethod
    def generate_new_account_keys(user_id: str = None) -> AccountKeys:
        user_id = user_id or str(uuid.uuid4())
        return AccountKeys(user_id=user_id, private_signing_key=SigningKey.generate())

    @staticmethod
    def save_single_account_keys(account_keys: AccountKeys, filename: Union[str, os.PathLike]) -> None:
        with open(filename, "w") as f:
            json.dump(account_keys.to_json(), f, indent=2)

    @staticmethod
    def load_single_account_keys(filename: Union[str, os.PathLike]) -> AccountKeys:
        with open(filename, "r") as f:
            account_keys_dict = json.load(f)
            return AccountKeys.from_json(account_keys_dict)

    @staticmethod
    def save_multiple_account_keys(keys: Iterable[AccountKeys], filename: Union[str, os.PathLike]) -> None:
        with open(filename, "w") as f:
            json.dump({a.user_id: a.to_json() for a in keys}, f, indent=2)

    @staticmethod
    def load_multiple_account_keys(filename: Union[str, os.PathLike]) -> Dict[str, AccountKeys]:
        with open(filename, "r") as f:
            data = json.load(f)
        for user_id in data.keys():
            data[user_id] = AccountKeys.from_json(data[user_id])

        return data

    @staticmethod
    def sign_blob(blob: bytes, private_signing_key: Union[SigningKey, bytes]) -> bytes:
        """
        Signs the blob that is passed and returns the signature.
        """
        private_signing_key: SigningKey = private_signing_key \
            if isinstance(private_signing_key, SigningKey) \
            else SigningKey(private_signing_key)
        return private_signing_key.sign(blob).signature

    @staticmethod
    def is_valid_signature(blob: bytes, signature: bytes, public_signing_key: Union[VerifyKey, bytes]) -> bool:
        """Verifies that the blob matches the signature for the given public key."""
        signing_key = public_signing_key \
            if isinstance(public_signing_key, VerifyKey) \
            else VerifyKey(public_signing_key)
        # noinspection PyBroadException
        try:
            signing_key.verify(blob, signature)
            return True
        except:
            return False

    @staticmethod
    def generate_symmetric_key() -> bytes:
        """Generates random bytes for symmetric encryption"""
        return nacl.utils.random(SecretBox.KEY_SIZE)

    @staticmethod
    def symmetric_encrypt_blob(blob: bytes, secret_symmetric_key: bytes) -> EncryptedMessage:
        """Encrypt blob with symmetric key."""
        return SecretBox(secret_symmetric_key).encrypt(blob)

    @staticmethod
    def symmetric_decrypt_blob(blob: Union[str, bytes, EncryptedMessage],
                               secret_symmetric_key: bytes) -> bytes:
        blob = bytes.fromhex(blob) if isinstance(blob, str) else blob  # Hex string to bytes
        return SecretBox(secret_symmetric_key).decrypt(blob)

    @staticmethod
    def authenticated_encrypt_blob(blob: bytes,
                                   sender_private_encryption_key: Union[PrivateKey, bytes],
                                   receiver_public_encryption_key: Union[PublicKey, bytes]) -> EncryptedMessage:
        sender_private_encryption_key = sender_private_encryption_key \
            if isinstance(sender_private_encryption_key, PrivateKey) \
            else PrivateKey(sender_private_encryption_key)
        receiver_public_encryption_key = receiver_public_encryption_key \
            if isinstance(receiver_public_encryption_key, PublicKey) \
            else PublicKey(receiver_public_encryption_key)
        box = Box(private_key=sender_private_encryption_key, public_key=receiver_public_encryption_key)
        return box.encrypt(blob)

    @staticmethod
    def authenticated_decrypt_blob(blob: Union[EncryptedMessage, str, bytes],
                                   receiver_private_encryption_key: Union[PrivateKey, bytes],
                                   sender_public_encryption_key: Union[PublicKey, bytes]) -> bytes:
        blob = bytes.fromhex(blob) if isinstance(blob, str) else blob
        receiver_private_encryption_key = receiver_private_encryption_key \
            if isinstance(receiver_private_encryption_key, PrivateKey) \
            else PrivateKey(receiver_private_encryption_key)
        sender_public_encryption_key = sender_public_encryption_key \
            if isinstance(sender_public_encryption_key, PublicKey) \
            else PublicKey(sender_public_encryption_key)
        box = Box(private_key=receiver_private_encryption_key, public_key=sender_public_encryption_key)
        return box.decrypt(blob)
