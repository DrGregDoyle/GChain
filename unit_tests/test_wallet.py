'''
Unit tests for the wallet class
'''
import secrets
import primefac
import numpy as np
from wallet import Wallet
from cryptography import EllipticCurve

'''
Test Vars
'''

BITCOIN_PRIME = pow(2, 256) - pow(2, 32) - pow(2, 9) - pow(2, 8) - pow(2, 7) - pow(2, 6) - pow(2, 4) - 1
BITCOIN_ECC_GENERATOR = (0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
                         0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)

'''
Tests
'''


def test_seed_phrase():
    test_seed_128 = secrets.randbits(128)
    test_seed_256 = secrets.randbits(256)

    wallet_128 = Wallet()
    wallet_256 = Wallet(bits=256, checksum_bits=8)

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


def test_ecc_keys():
    '''
    We verify that we retrieve the correct prime and generator
    We verify that the private key corresponds to public key through elliptic discrete log
    '''
    wallet_ecc = Wallet()

    [(s_x, s_y), (s_gx, s_gy), s_p], s_k = wallet_ecc.master_keys

    (x, y) = (int(s_x, 16), int(s_y, 16))
    (gx, gy) = (int(s_gx, 16), int(s_gy, 16))
    p = int(s_p, 16)
    k = int(s_k, 16)

    assert p == BITCOIN_PRIME
    assert (gx, gy) == BITCOIN_ECC_GENERATOR

    curve = EllipticCurve(a=0, b=7, p=BITCOIN_PRIME)
    point = curve.scalar_multiplication(k, BITCOIN_ECC_GENERATOR)

    assert point == (x, y)


def test_dl_keys():
    '''
    We verify that we get back the correct prime
    We verify that the private key corresponds to the public key using discrete log

    '''
    wallet_dl = Wallet(use_ecc=False, use_dl=True)

    [s_k, s_g, s_p], s_K = wallet_dl.master_keys

    k = int(s_k, 16)
    g = int(s_g, 16)
    p = int(s_p, 16)
    K = int(s_K, 16)

    assert p == BITCOIN_PRIME

    generator_val = pow(g, K, p)
    assert generator_val == k


def test_rsa_keys():
    '''
    We verify the above and below vals are prime
    '''
    pass
    # wallet_rsa = Wallet(use_ecc=False, use_rsa=True)
    # [(s_e, s_n)], s_d = wallet_rsa.master_keys
    # e = int(s_e, 16)
    # n = int(s_n, 16)
    # d = int(s_d, 16)
    #
    # message = secrets.randbits(256)
    # print(message)
