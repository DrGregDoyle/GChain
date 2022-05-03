'''
Various helper functions I don't know where else to put.
'''

'''
IMPORTS
'''
from vli import VLI
from hashlib import sha256
import datetime


def get_signature_parts(signature: str, index0=0):
    '''
    A static method to read in a signature. We return the hex string values of the compressed public key and (r,s).
    '''

    # Read in compressed public key VLI
    index1 = index0 + 2
    cpk_first_byte = signature[index0:index1]

    if int(cpk_first_byte, 16) < 253:
        cpk_length = int(cpk_first_byte, 16)
    else:
        index_adjust = VLI.first_byte_index(int(cpk_first_byte, 16))
        cpk_length = int(signature[index1:index1 + index_adjust], 16)
        index1 = index1 + index_adjust

    # Read in compressed public key
    index2 = index1 + cpk_length
    compressed_public_key = signature[index1: index2]

    # Read in r VLI
    index3 = index2 + 2
    r_first_byte = signature[index2:index3]

    if int(r_first_byte, 16) < 253:
        r_length = int(r_first_byte, 16)
    else:
        r_index_adjust = VLI.first_byte_index(int(r_first_byte, 16))
        r_length = int(signature[index3:index3 + r_index_adjust])
        index3 = index3 + r_index_adjust

    # Read in r as hex string
    index4 = index3 + r_length
    r_hex = signature[index3:index4]

    # Read in s VLI
    index5 = index4 + 2
    s_first_byte = signature[index4:index5]

    if int(s_first_byte, 16) < 253:
        s_length = int(s_first_byte, 16)
    else:
        s_index_adjust = VLI.first_byte_index(int(s_first_byte, 16))
        s_length = int(signature[index5:index5 + s_index_adjust])
        index5 = index5 + s_index_adjust

    # Read in s
    index6 = index5 + s_length
    s_hex = signature[index5:index6]

    return compressed_public_key, (r_hex, s_hex)


def verify_address_checksum(address: str, ADDRESS_DIGEST_BITS=160, CHECKSUM_BITS=32) -> bool:
    '''
    We get a base58 encoded address and we verify it the attached checksum matches the address
    '''

    # Get hex string
    hex_address = base58_to_int(address)

    # Get address digest
    digest = hex_address[:ADDRESS_DIGEST_BITS // 4]
    checksum = hex_address[ADDRESS_DIGEST_BITS // 4: CHECKSUM_BITS // 4]

    # Find the checksum from the digest
    digest_checksum = sha256(sha256(digest.encode()).hexdigest()).hexdigest()[:CHECKSUM_BITS // 4]

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
