'''
Various helper functions I don't know where else to put.
'''

'''
IMPORTS
'''
from vli import VLI


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
