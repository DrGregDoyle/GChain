'''
Test for the various helper functions
'''

from helpers import int_to_base58, base58_to_int
import secrets


def test_base58():
    num1 = secrets.randbits(256)
    addy1 = int_to_base58(num1)
    num2 = base58_to_int(addy1)
    assert num1 == num2

    hex_val = hex(num2)[2:]
    addy2 = int_to_base58(int(hex_val, 16))
    assert addy1 == addy2
