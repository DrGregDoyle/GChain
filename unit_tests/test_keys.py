'''
Unit tests for cryptographic key methods
'''

from cryptography import generate_ecc_keys, EllipticCurve
from hashlib import sha256


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
