'''
Unit tests for the wallet class
'''

'''
Imports
'''
import secrets
import numpy as np
from wallet import Wallet
from hashlib import sha256

'''
Tests
'''


def test_seed_phrase():
    test_seed_128 = secrets.randbits(128)
    test_seed_256 = secrets.randbits(256)

    wallet_128 = Wallet()
    wallet_256 = Wallet(bits=256, seed_checksum_bits=8)

    phrase_128 = wallet_128.get_seed_phrase(test_seed_128)
    seed_128 = wallet_128.recover_seed(phrase_128)

    phrase_256 = wallet_256.get_seed_phrase(test_seed_256)
    seed_256 = wallet_256.recover_seed(phrase_256)

    assert wallet_128.get_seed_phrase(seed_128) == phrase_128
    assert wallet_256.get_seed_phrase(seed_256) == phrase_256


def test_entropy_checksum_mod11():
    random_num = 0
    while random_num % 11 == 0:
        random_num = np.random.randint(150, 250)

    w1 = Wallet()
    w2 = Wallet(256, 8)
    w3 = Wallet(50, 5)
    w4 = Wallet(128, 8)
    w5 = Wallet(random_num, 0)
    w6 = Wallet(165, 0)

    # Default case
    assert w1.bits == 128
    assert w1.seed_checksum_bits == 4

    # Case where both bits and checksum are correct
    assert w2.bits == 256
    assert w2.seed_checksum_bits == 8

    # Case where bits are invalid, checksum is not
    assert w3.bits == 128
    assert w3.seed_checksum_bits == 4

    # Case where bits are valid, checksum is not
    assert w4.bits == 128
    assert w4.seed_checksum_bits == 4

    # Tests case where bits are random valid number not congruent to 0 (mod 11) yields correct checksum
    assert w5.bits == random_num
    assert w5.seed_checksum_bits == -random_num % 11

    # Tests case where bits = 0 (mod 11). Want a nonzero checksum_bits
    assert w6.bits == 165
    assert w6.seed_checksum_bits == 11


def test_keys():
    w = Wallet()
    (hx, hy), hex_priv = w.master_keys
    x = int(hx, 16)
    y = int(hy, 16)
    int_pub = (x, y)
    int_priv = int(hex_priv, 16)
    assert w.curve.scalar_multiplication(int_priv, w.curve.generator) == int_pub


def test_signature():
    w = Wallet()
    tx_hash1 = sha256('tx_hash'.encode()).hexdigest()
    tx_hash2 = sha256('bad_hash'.encode()).hexdigest()

    sig = w.sign_transaction(tx_hash1)
    assert w.verify_signature(sig, tx_hash1)
    assert not w.verify_signature(sig, tx_hash2)
