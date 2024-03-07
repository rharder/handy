#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tempfile
from pathlib import Path
from unittest import TestCase

import nacl.exceptions

from handy.key_utils import KeyUtility


class TestKeyUtils(TestCase):

    def test_signing(self):
        acct1 = KeyUtility.generate_new_account_keys("user1")
        acct2 = KeyUtility.generate_new_account_keys("user2")
        self.assertNotEqual(acct1.public_signing_key_bytes, acct2.public_signing_key_bytes)

        # Proper signature
        msg1 = b"Hello World"
        sig1 = acct1.sign_blob(msg1)
        self.assertTrue(acct1.is_valid_signature(msg1, sig1))
        self.assertTrue(KeyUtility.is_valid_signature(msg1, sig1, acct1.public_signing_key))

        # Returns false when compared against wrong acct keys
        self.assertFalse(acct2.is_valid_signature(blob=msg1, signature=sig1))
        self.assertFalse(KeyUtility.is_valid_signature(blob=msg1, signature=sig1,
                                                       public_signing_key=acct2.public_signing_key))

        # Original message was modified, won't pass
        tampered_msg1 = b"Goodbye World"
        self.assertFalse(acct1.is_valid_signature(tampered_msg1, sig1))
        self.assertFalse(KeyUtility.is_valid_signature(tampered_msg1, sig1, acct1.public_signing_key))

    def test_encrypt(self):
        alice = KeyUtility.generate_new_account_keys("alice")
        bob = KeyUtility.generate_new_account_keys("bob")

        # Alice has a message for Bob
        msg1 = b"Hello World"
        alice_has_bob_public_key = bob.public_encryption_key_bytes
        encr_msg = alice.authenticated_encrypt_blob(blob=msg1,
                                                    receiver_public_encryption_key=alice_has_bob_public_key)
        msg_passed_in_the_clear = encr_msg.hex()  # 0ec71a3887ceb12be6b...

        # Bob gets message from the wild
        bob_has_alice_public_key = alice.public_encryption_key_bytes
        decr_msg = bob.authenticated_decrypt_blob(blob=msg_passed_in_the_clear,
                                                  sender_public_encryption_key=bob_has_alice_public_key)
        self.assertEqual(msg1, decr_msg)  # Bob gets Hello World message
        # Decrypt with static function also
        decr_msg = KeyUtility.authenticated_decrypt_blob(blob=msg_passed_in_the_clear,
                                                         sender_public_encryption_key=bob_has_alice_public_key,
                                                         receiver_private_encryption_key=bob.private_encryption_key)
        self.assertEqual(msg1, decr_msg)  # Bob gets Hello World message

        # Eve modifies messasge in transit
        msg_modified_by_eve = b"evil".hex() + msg_passed_in_the_clear
        with self.assertRaises(nacl.exceptions.CryptoError):
            bob.authenticated_decrypt_blob(blob=msg_modified_by_eve,
                                           sender_public_encryption_key=bob_has_alice_public_key)

        # Eve cannot read message with anything she tries
        for attempted_key in (
                b"Z" * 31,  # Invalid number of bytes in key
                b"Z" * 32,  # Right number of bytes but bogus key
                alice.public_encryption_key_bytes,  # Nope, not her public key
                bob.public_encryption_key_bytes,  # Nope, not his public key
                KeyUtility.generate_new_account_keys().private_encryption_key  # Nope, not another private key
        ):
            with self.assertRaises(Exception):
                KeyUtility.authenticated_decrypt_blob(blob=msg_passed_in_the_clear,
                                                      sender_public_encryption_key=alice.public_encryption_key_bytes,
                                                      receiver_private_encryption_key=attempted_key)

    def test_save_account_data(self):
        acct1 = KeyUtility.generate_new_account_keys("user1")
        acct2 = KeyUtility.generate_new_account_keys("user2")
        acct3 = KeyUtility.generate_new_account_keys("user3")
        self.assertNotEqual(acct1, acct2)
        self.assertNotEqual(acct1, acct3)
        self.assertNotEqual(acct2, acct3)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save a file and recover it
            tmpdir: Path = Path(tmpdir)
            file1 = tmpdir / "file1.json"
            KeyUtility.save_single_account_keys(acct1, file1)
            acct1a = KeyUtility.load_single_account_keys(file1)
            self.assertEqual(acct1, acct1a)

            # Save multiple and recover them
            file_all = tmpdir / "file_all.json"
            KeyUtility.save_multiple_account_keys([acct1, acct2, acct3], file_all)
            accts_read = KeyUtility.load_multiple_account_keys(file_all)
            self.assertEqual(3, len(accts_read))
            self.assertEqual(acct1, accts_read[acct1.user_id])
            self.assertEqual(acct2, accts_read[acct2.user_id])
            self.assertEqual(acct3, accts_read[acct3.user_id])
