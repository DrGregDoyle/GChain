'''
The UTXO Class

We will use hex strings in order to track byte count.
All hex char's can be expressed uniquely using 4 bits
Hence 2 hex characters = 1 byte


Hence:

Bit size    | Byte Size     | hex characters        | field
===========================================================
256         | 32            | 64                   | tx_id
32          | 4             | 8                    | tx_index
64          | 8             | 16                    | script_length
var         | var           | var                   | signature_script
32          | 4             | 8                    | sequence


#TODO: Change script_length to variable length integer
Variable length integer:

The way the variable length integer works is:
    Look at the first byte
    If that first byte is less than 253, use the byte literally
    If that first byte is 253, read the next two bytes as a little endian 16-bit number (total bytes read = 3)
    If that first byte is 254, read the next four bytes as a little endian 32-bit number (total bytes read = 5)
    If that first byte is 255, read the next eight bytes as a little endian 64-bit number (total bytes read = 9)



'''
import secrets

'''Imports'''
from hashlib import sha256


class UTXO:
    '''
    Class Vars. Hardcoded for now
    '''
    TRANSACTION_BYTES = 32
    INDEX_BYTES = 4
    LENGTH_BYTES = 8
    SEQUENCE_BYTES = 4

    def __init__(self, tx_id: str, tx_index: int, signature_script: str, sequence: int):
        self.tx_id = tx_id
        self.tx_index = format(tx_index, f'0{2 * self.INDEX_BYTES}x')

        '''If the hex string has odd parity, it won't be an even number of bytes'''
        '''Prepend 0 if hex string has odd length. This yields full byte count'''
        if len(signature_script) % 2 == 1:
            signature_script = '0' + signature_script
        self.signature_script = signature_script

        self.script_length = format(len(self.signature_script) // 2, f'0{2 * self.LENGTH_BYTES}x')
        self.sequence = format(sequence, f'0{2 * self.SEQUENCE_BYTES}x')

    def get_raw_utxo(self):
        return self.tx_id + self.tx_index + self.script_length + self.signature_script + self.sequence

    def get_hex_chars(self):
        return len(self.get_raw_utxo())


class OUTPUT_UTXO:
    AMOUNT_BYTES = 8
    LENGTH_BYTES = 8

    def __init__(self, amount: int, unlock_script: str):
        '''
        The amount is the amount owned.
        The unlock script contains the address
        '''
        self.amount = format(amount, f'0{2 * self.AMOUNT_BYTES}x')
        '''Handle odd script parity for full byte count'''
        if len(unlock_script) % 2 == 1:
            unlock_script = '0' + unlock_script
        self.unlock_script = unlock_script

        self.script_length = format(len(self.unlock_script) // 2, f'0{2 * self.LENGTH_BYTES}x')

    def get_raw_output(self):
        return self.amount + self.script_length + self.unlock_script

    def get_hex_chars(self):
        return len(self.get_raw_output())


'''
Unpack
'''


def decode_raw_utxo(raw_utxo: str, TRANSACTION_BYTES=32, INDEX_BYTES=4, LENGTH_BYTES=8, SEQUENCE_BYTES=4):
    '''
    We read in the hex strings and create the corresponding UTXO
    '''
    index1 = TRANSACTION_BYTES * 2
    index2 = index1 + INDEX_BYTES * 2
    index3 = index2 + LENGTH_BYTES * 2

    tx_id = raw_utxo[0:index1]
    tx_index = int(raw_utxo[index1:index2], 16)
    script_length = int(raw_utxo[index2:index3], 16)

    index4 = index3 + 2 * script_length
    index5 = index4 + 2 * SEQUENCE_BYTES

    signature_script = raw_utxo[index3: index4]
    sequence = int(raw_utxo[index4:index5], 16)

    return UTXO(tx_id, tx_index, signature_script, sequence)


def decode_raw_output(raw_output: str, AMOUNT_BYTES=8, LENGTH_BYTES=8):
    '''
    We read in the hex string and create the output utxo
    '''

    index1 = 2 * AMOUNT_BYTES
    index2 = index1 + 2 * LENGTH_BYTES

    amount = int(raw_output[0:index1], 16)
    script_length = int(raw_output[index1:index2], 16)

    index3 = index2 + 2 * script_length

    unlock_script = raw_output[index2:index3]

    return OUTPUT_UTXO(amount, unlock_script)


'''
TESTING
'''


def test():
    tx_id = sha256('Transaction'.encode()).hexdigest()
    tx_index = 0
    sig_script = sha256('SignatureScript'.encode()).hexdigest()
    utxo = UTXO(tx_id, tx_index, sig_script)
    return utxo


def output_test():
    amount = 10
    unlock_script = hex(secrets.randbits(320))[2:]
    output = OUTPUT_UTXO(amount, unlock_script)
    return output
