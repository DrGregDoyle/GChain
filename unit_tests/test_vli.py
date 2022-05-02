'''
Testing VLI string
'''

'''
IMPORTS
'''
import secrets
from vli import VLI

'''
TESTING
'''


def test_vli():
    '''

    '''
    int1 = secrets.randbelow(pow(2, 8) - 3)
    int2 = 253
    int3 = secrets.randbelow(pow(2, 16))
    int4 = pow(2, 16)
    int5 = secrets.randbelow(pow(2, 32))
    int6 = pow(2, 32)
    int7 = secrets.randbelow(pow(2, 64))
    int8 = pow(2, 64)
    int9 = -1

    # Test 1 - random int belo 253
    string1 = VLI(int1).vli_string
    assert string1 == format(int1, '02x')

    # Test 2 - int == 253
    string2 = VLI(int2).vli_string
    assert string2 == "FD" + format(int2, '04x')

    # Test 3  - 253 <= random_int < 2^16
    while int3 < pow(2, 8) - 1:
        int3 = secrets.randbelow(pow(2, 16))
    string3 = VLI(int3).vli_string
    assert string3 == "FD" + format(int3, '04x')

    # Test 4 - int == 2^16
    string4 = VLI(int4).vli_string
    assert string4 == "FE" + format(int4, '08x')

    # Test 5 - 2^16 <= random_int < 2^32
    while int5 < pow(2, 16):
        int5 = secrets.randbelow(pow(2, 32))
    string5 = VLI(int5).vli_string
    assert string5 == "FE" + format(int5, '08x')

    # Test 6 - int == 2^32
    string6 = VLI(int6).vli_string
    assert string6 == "FF" + format(int6, '016x')

    # Test 7 - 2^32 <= random_int < 2^64
    string7 = VLI(int7).vli_string
    assert string7 == "FF" + format(int7, '016x')

    # Test 8 - int = 2^64
    string8 = VLI(int8).vli_string
    assert string8 is None

    # Test9 - int = 0
    string9 = VLI(int9).vli_string
    assert string9 is None
