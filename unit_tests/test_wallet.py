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
from helpers import get_signature_parts

'''
Tests
'''


def test_seed_phrase():
    '''
    We test the seed generation and seed recovery functions for 128 and 256 seed_bits
    '''

    # 128 Bits
    seed_128 = 0
    while seed_128.bit_length() != 128:
        seed_128 = secrets.randbits(128)

    wallet_from_seed_128 = Wallet(seed=seed_128)
    assert wallet_from_seed_128.recover_seed(wallet_from_seed_128.seed_phrase) == seed_128

    # 256 Bits
    seed_256 = 0
    while seed_256.bit_length() != 256:
        seed_256 = secrets.randbits(256)

    wallet_from_seed_256 = Wallet(seed_bits=256, seed=seed_256)
    assert wallet_from_seed_256.recover_seed(wallet_from_seed_256.seed_phrase) == seed_256


def test_entropy_checksum_mod11():
    random_num = 0
    while random_num % 11 == 0:
        random_num = np.random.randint(150, 250)

    w1 = Wallet()
    w2 = Wallet(seed_bits=256)
    w3 = Wallet(seed_bits=50)
    w4 = Wallet(seed_bits=128)
    w5 = Wallet(seed_bits=random_num)
    w6 = Wallet(seed_bits=165)

    # Default case
    assert w1.seed_bits == 128
    assert w1.seed_checksum_bits == 4

    # Case where both bits and checksum are correct
    assert w2.seed_bits == 256
    assert w2.seed_checksum_bits == 8

    # Case where bits are invalid, checksum is not
    assert w3.seed_bits == 128
    assert w3.seed_checksum_bits == 4

    # Case where bits are valid, checksum is not
    assert w4.seed_bits == 128
    assert w4.seed_checksum_bits == 4

    # Tests case where bits are random valid number not congruent to 0 (mod 11) yields correct checksum
    assert w5.seed_bits == random_num
    assert w5.seed_checksum_bits == -random_num % 11

    # Tests case where bits = 0 (mod 11). Want a nonzero checksum_bits
    assert w6.seed_bits == 165
    assert w6.seed_checksum_bits == 11


def test_signature():
    w = Wallet()
    tx_hash1 = sha256('tx_hash'.encode()).hexdigest()
    tx_hash2 = sha256('bad_hash'.encode()).hexdigest()

    sig = w.sign_transaction(tx_hash1)
    cpk, (r_h, s_h) = get_signature_parts(sig)
    r = int(r_h, 16)
    s = int(s_h, 16)
    sig = (r, s)

    assert w.curve.verify_signature(sig, tx_hash1, w.public_key_point)
    assert not w.curve.verify_signature(sig, tx_hash2, w.public_key_point)
