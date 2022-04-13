'''
Unit tests for cryptographic key methods
'''

from cryptography import generate_rsa_keys, generate_dl_keys, generate_ecc_keys, EllipticCurve
from hashlib import sha256


def test_rsa_keys():
    rsa_public, rsa_private = generate_rsa_keys()
    h_e, h_n = rsa_public
    h_d = rsa_private

    e = int(h_e, 16)
    n = int(h_n, 16)
    d = int(h_d, 16)

    message = 'Hello world!'
    hash = sha256(message.encode()).hexdigest()
    hash_int = int(hash, 16)

    encoded_num = pow(hash_int, e, n)
    decoded_num = pow(encoded_num, d, n)
    assert hex(decoded_num)[2:] == hash


def test_dl_keys():
    dl_public, dl_private = generate_dl_keys(128)  # Finding generator hard for large p

    h_k, h_g, h_p = dl_public
    h_d = dl_private

    k = int(h_k, 16)
    g = int(h_g, 16)
    p = int(h_p, 16)
    d = int(h_d, 16)

    assert pow(g, d, p) == k


def test_ecc_keys():
    ecc_public, ecc_private = generate_ecc_keys()
    hex_point1, hex_point2, h_p = ecc_public
    h_x, h_y = hex_point1
    h_gx, h_gy = hex_point2
    h_k = ecc_private

    x = int(h_x, 16)
    y = int(h_y, 16)
    gx = int(h_gx, 16)
    gy = int(h_gy, 16)
    p = int(h_p, 16)
    k = int(h_k, 16)

    curve = EllipticCurve(0, 7, p)
    point = (x, y)
    generator = (gx, gy)

    assert curve.scalar_multiplication(k, generator) == point
