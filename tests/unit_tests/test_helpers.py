'''
Test for the various helper functions
'''

'''
IMPORTS
'''
from helpers import int_to_base58, base58_to_int, get_signature_parts, verify_address_checksum
import secrets
from wallet import Wallet
from tests.testing_functions import generate_transaction

'''
TESTS
'''


def test_base58():
    num1 = secrets.randbits(256)
    addy1 = int_to_base58(num1)
    num2 = base58_to_int(addy1)
    assert num1 == num2

    hex_val = hex(num2)[2:]
    addy2 = int_to_base58(int(hex_val, 16))
    assert addy1 == addy2


def test_signature_parts():
    tx = generate_transaction()
    w = Wallet()
    sig = w.sign_transaction(tx.id)
    cpk, (r_h, s_h) = get_signature_parts(sig)
    r = int(r_h, 16)
    s = int(s_h, 16)
    assert cpk == w.compressed_public_key
    assert w.curve.verify_signature((r, s), tx.id, w.curve.get_public_key_point(cpk))


def test_address():
    w = Wallet()
    addy = w.address
    assert verify_address_checksum(addy)
