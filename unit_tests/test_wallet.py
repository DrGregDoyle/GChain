'''
Unit tests for the wallet class
'''

import numpy as np
from wallet import Wallet


def test_seed_phrase():
    wallet_128 = Wallet()
    wallet_256 = Wallet(bits=256, checksum_bits=8)

    phrase_128 = wallet_128.get_seed_phrase()
    seed_128 = wallet_128.recover_seed(phrase_128)

    phrase_256 = wallet_256.get_seed_phrase()
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
    assert w1.checksum_bits == 4

    # Case where both bits and checksum are correct
    assert w2.bits == 256
    assert w2.checksum_bits == 8

    # Case where bits are invalid, checksum is not
    assert w3.bits == 128
    assert w3.checksum_bits == 4

    # Case where bits are valid, checksum is not
    assert w4.bits == 128
    assert w4.checksum_bits == 4

    # Tests case where bits are random valid number not congruent to 0 (mod 11) yields correct checksum
    assert w5.bits == random_num
    assert w5.checksum_bits == -random_num % 11

    # Tests case where bits = 0 (mod 11). Want a nonzero checksum_bits
    assert w6.bits == 165
    assert w6.checksum_bits == 11
