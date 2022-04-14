'''
Unit tests for the wallet class
'''

import io
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
