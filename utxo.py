'''
The UTXO Class

We divide the Class into two objects: Inputs and Outputs


Byte Size / Bit Size    |   Variable
=============================
INPUT
-----
32 bytes / 256 bits     | tx_id (previous transaction hash)
4 bytes / 32 bits       | tx_index (index number of input utxo)
8 bytes / 64 bits   | Byte length of unlocking script   TODO: Implement variable length integer
var                     | unlocking script
4 bytes / 32 bits       |sequence number   (set to 0xFFFFFFFF)

OUTPUT
------
8 bytes / 64 bits       | amount    (for output)
8 bytes / 64 bits   | byte length of signature script   TODO: Implement variable length integer
var                     | signature script

Variable length integer:
/********************\
The way the variable length integer works is:

Look at the first byte
If that first byte is less than 253, use the byte literally
If that first byte is 253, read the next two bytes as a little endian 16-bit number (total bytes read = 3)
If that first byte is 254, read the next four bytes as a little endian 32-bit number (total bytes read = 5)
If that first byte is 255, read the next eight bytes as a little endian 64-bit number (total bytes read = 9)
\*********************/



'''

'''Imports'''
import string
from hashlib import sha256

'''Classes'''


class UTXO:

    def __init__(self, tx_id: str, tx_index: int, unlocking_script: str, sequence=0xffffffff, tx_bits=256,
                 index_bits=32, sequence_bits=32, unlock_length_bits=64):
        '''
        We create a new input. It must match with the transaction output in the tx_id/tx_index referenced
        '''

        self.tx_id = tx_id
        self.tx_index = tx_index
        self.unlocking_script = unlocking_script
        self.sequence = sequence

        self.tx_bits = tx_bits
        self.index_bits = index_bits
        self.sequence_bits = sequence_bits
        self.unlock_length_bits = unlock_length_bits

    def get_raw_utxo(self):
        '''
        We write all our values in binary, then return the hex value
        '''

        '''Transaction Id'''
        binary_transactions = bin(int(self.tx_id, 16))[2:]
        assert len(binary_transactions) == self.tx_bits

        '''Transaction Index'''
        binary_index = format(self.tx_index, f'0{self.index_bits}b')
        assert len(binary_index) == self.index_bits

        '''Unlocking Script'''
        unlock_script_int = int(self.unlocking_script, 16)
        unlock_bitlength = unlock_script_int.bit_length()
        binary_unlock_length = format(unlock_bitlength, f'0{self.unlock_length_bits}b')
        assert len(binary_unlock_length) == self.unlock_length_bits
        binary_unlock = bin(unlock_script_int)[2:]

        '''Sequence'''
        assert self.sequence.bit_length() == self.sequence_bits
        binary_sequence = bin(self.sequence)[2:]

        binary_utxo = binary_transactions + binary_index + binary_unlock_length + binary_unlock + binary_sequence
        return hex(int(binary_utxo, 2))


'''
Unpack
'''


def decode_raw_utxo(raw_utxo: str, tx_bits=256, index_bits=32, sequence_bits=32, unlock_length_bits=64):
    '''
    Using default bit size. This can be variable
    '''
    binary_string = bin(int(raw_utxo, 16))[2:]

    index1 = tx_bits
    index2 = index1 + index_bits
    index3 = index2 + unlock_length_bits

    binary_transactions = binary_string[0:index1]
    binary_index = binary_string[index1: index2]
    binary_unlock_length = binary_string[index2: index3]

    unlock_script_bits = int(binary_unlock_length, 2)
    index4 = index3 + unlock_script_bits
    index5 = index4 + sequence_bits

    binary_unlock_script = binary_string[index3:index4]
    binary_sequence = binary_string[index4:index5]

    tx_id = hex(int(binary_transactions, 2))[2:]
    tx_index = int(binary_index, 2)
    unlock_script = hex(int(binary_unlock_script, 2))[2:]
    sequence = int(binary_sequence, 2)

    return UTXO(tx_id, tx_index, unlock_script, sequence, tx_bits, index_bits, sequence_bits, unlock_length_bits)


'''
Testing
'''


def test():
    tx_id = sha256('transaction id'.encode()).hexdigest()
    index = 0
    unlock_script = sha256('unlock script'.encode()).hexdigest()
    utxo = UTXO(tx_id, index, unlock_script)
    return utxo
