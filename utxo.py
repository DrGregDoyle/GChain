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
from hashlib import sha256


class UTXO:
    '''
    Class Vars. Hardcoded for now
    '''
    TRANSACTION_BYTES = 32
    INDEX_BYTES = 4
    LENGTH_BYTES = 8
    SEQUENCE_BYTES = 4

    def __init__(self, tx_id: str, tx_index: int, signature_script: str, sequence=None):
        self.tx_id = tx_id
        self.tx_index = format(tx_index, f'0{2 * self.INDEX_BYTES}x')
        self.signature_script = signature_script
        self.script_length = format(len(self.signature_script) // 2, f'0{2 * self.LENGTH_BYTES}x')
        if sequence is None:
            self.sequence = format(0xffffffff, f'0{2 * self.SEQUENCE_BYTES}x')
        else:
            self.sequence = format(sequence, f'0{2 * self.SEQUENCE_BYTES}x')

    def get_raw_utxo(self):
        return self.tx_id + self.tx_index + self.script_length + self.signature_script + self.sequence


'''
TESTING
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


def test():
    tx_id = sha256('Transaction'.encode()).hexdigest()
    tx_index = 0
    sig_script = sha256('SignatureScript'.encode()).hexdigest()
    utxo = UTXO(tx_id, tx_index, sig_script)
    return utxo
