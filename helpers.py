'''
Various helper functions I don't know where else to put.
'''

'''
IMPORTS
'''
from vli import VLI
from hashlib import sha256
import datetime


def get_signature_parts(signature: str):
    '''
    A static method to read in a signature. We return the hex string values of the compressed public key and (r,s).
    '''
    cpk_length = int(signature[:2], 16)
    cpk = signature[2:2 + cpk_length]
    r_length = int(signature[2 + cpk_length:4 + cpk_length], 16)
    r = signature[4 + cpk_length:4 + cpk_length + r_length]
    s_length = int(signature[4 + cpk_length + r_length:6 + cpk_length + r_length], 16)
    s = signature[6 + cpk_length + r_length:6 + cpk_length + r_length + s_length]

    return cpk, (r, s)


def verify_address_checksum(address: str, ADDRESS_DIGEST_BITS=160, CHECKSUM_BITS=32) -> bool:
    '''
    We get a base58 encoded address and we verify it the attached checksum matches the address
    '''

    # Get hex string
    hex_address = hex(base58_to_int(address))[2:]
    if len(hex_address) != ADDRESS_DIGEST_BITS // 4 + CHECKSUM_BITS // 4:
        hex_address = '0' + hex_address

    # Get address digest
    digest = hex_address[:ADDRESS_DIGEST_BITS // 4]
    checksum = hex_address[ADDRESS_DIGEST_BITS // 4: CHECKSUM_BITS // 4]

    # Find the checksum from the digest
    digest_checksum = sha256(sha256(digest.encode()).hexdigest().encode()).hexdigest()[:CHECKSUM_BITS // 4]

    return digest_checksum == checksum


BASE58_LIST = ['1', '2', '3', '4', '5', '6', '7', '8', '9',
               'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J',
               'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T',
               'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c',
               'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'm',
               'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v',
               'w', 'x', 'y', 'z']


def int_to_base58(num: int) -> str:
    '''
    Explanation here
    '''
    base58_string = ''
    num_copy = num
    # If num_copy is negative, keep adding 58 until it isn't
    # Negative numbers will always result in a single residue
    # Maybe think about returning error. No negative integer should ever be used.
    while num_copy < 0:
        num_copy += 58
    if num_copy == 0:
        base58_string = '1'
    else:
        while num_copy > 0:
            remainder = num_copy % 58
            base58_string = BASE58_LIST[remainder] + base58_string
            num_copy = num_copy // 58
    return base58_string


def base58_to_int(base58_string: str) -> int:
    '''
    To convert a base58 string back to an int:
        -For each character, find the numeric index in the list
        -Multiply this numeric value by a corresponding power of 58
        -Sum all values
    '''

    sum = 0
    for x in range(0, len(base58_string)):
        numeric_val = BASE58_LIST.index(base58_string[x:x + 1])
        sum += numeric_val * pow(58, len(base58_string) - x - 1)
    return sum


'''
Datetime Converter
'''


def utc_to_seconds():
    date_string = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    date_object = datetime.datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S%z')
    return int(date_object.timestamp())


def seconds_to_utc(seconds: int):
    date_object = datetime.datetime.utcfromtimestamp(seconds)
    return date_object.isoformat()
