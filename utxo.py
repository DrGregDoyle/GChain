'''
The UTXO Classes

We divide the UTXO into two classes: UTXO_INPUT, UTXO_OUTPUT.

The UTXO_INPUT has the following fields w corresponding size:

#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  tx_id       |   256         |   64          |   32              |#
#|  tx_index    |   32          |   8           |   4               |#
#|  sig_length  |   var         |   var         |   var             |#
#|  signature   |   var         |   var         |   var             |#
#|  sequence    |   32          |   8           |   4               |#
#====================================================================#


The UTXO_OUTPUT has the following fields w corresponding size:

#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  amount      |   32          |   8           |   4               |#
#|  unlock_len  |   var         |   var         |   var             |#
#|unlock_script |   var         |   var         |   var             |#
#====================================================================#


NB: Both sig_length and unlock_len will be the length in BYTES

'''


class UTXO_INPUT:
    '''

    '''
    TX_ID_BITS = 256
    TX_INDEX_BITS = 32
    SEQUENCE_BITS = 32

    def __init__(self, tx_id: str, tx_index: int, signature: str, sequence=0xffffffff):
        # Format transaction id, index and sequence
        self.tx_id = format(int(tx_id, 16), f'0{self.TX_ID_BITS // 4}x')
        self.tx_index = format(tx_index, f'0{self.TX_INDEX_BITS // 4}x')
        self.sequence = format(sequence, f'0{self.SEQUENCE_BITS // 4}x')

        # Get signature length from number of hex chars
        self.signature = signature
        if len(self.signature) % 2 == 1:
            self.signature = '0' + self.signature

        # Use variable length integer for byte length of signature
        byte_length = len(self.signature) // 2
        if byte_length < pow(2, 8) - 3:
            self.sig_length = format(byte_length, '02x')
        elif pow(2, 8) - 3 <= byte_length <= pow(2, 16):
            self.sig_length = 'FD' + format(byte_length, '04x')
        elif pow(2, 16) < byte_length <= pow(2, 32):
            self.sig_length = 'FE' + format(byte_length, '08x')
        else:
            self.sig_length = 'FF' + format(byte_length, '016x')

    '''
    Properties
    '''

    @property
    def raw_utxo(self):
        return self.tx_id + self.tx_index + self.sig_length + self.signature + self.sequence

    @property
    def byte_size(self):
        return len(self.raw_utxo) // 2


class UTXO_OUTPUT:
    '''

    '''
    AMOUNT_BITS = 32

    def __init__(self, amount: int, locking_script: str):
        # Format amount
        self.amount = format(amount, f'0{self.AMOUNT_BITS // 4}x')

        # Make sure locking script has full number of bytes
        self.locking_script = locking_script
        if len(self.locking_script) % 2 == 1:
            self.locking_script = '0' + self.locking_script

        # Use variable length integer for byte length of signature
        byte_length = len(self.locking_script) // 2
        if byte_length < pow(2, 8) - 3:
            self.script_length = format(byte_length, '02x')
        elif pow(2, 8) - 3 <= byte_length <= pow(2, 16):
            self.script_length = 'FD' + format(byte_length, '04x')
        elif pow(2, 16) < byte_length <= pow(2, 32):
            self.script_length = 'FE' + format(byte_length, '08x')
        else:
            self.script_length = 'FF' + format(byte_length, '016x')

    '''
    Properties
    '''

    @property
    def raw_utxo(self):
        return self.amount + self.script_length + self.locking_script

    @property
    def byte_size(self):
        return len(self.raw_utxo) // 2


'''
DECODE RAW UTXOS
'''


def decode_raw_input_utxo(input_utxo: str):
    '''
    The string will be given in hex characters and the UTXO_INPUT constants are bit sizes.
    Divide the bit size by 4 to get the number of hex characters
    '''
    # Create known indices first
    index1 = UTXO_INPUT.TX_ID_BITS // 4
    index2 = index1 + UTXO_INPUT.TX_INDEX_BITS // 4

    # Get the hash and index
    tx_id = input_utxo[:index1]
    tx_index = int(input_utxo[index1:index2], 16)

    # Get the variable length integer
    first_byte = int(input_utxo[index2:index2 + 2], 16)
    sig_length = first_byte
    if first_byte < 253:
        index3 = index2 + 2
    elif first_byte == 253:
        sig_length = int(input_utxo[index2 + 2:index2 + 4], 16)
        index3 = index2 + 4
    elif first_byte == 254:
        sig_length = int(input_utxo[index2 + 2:index2 + 8], 16)
        index3 = index2 + 8
    else:
        assert first_byte == 255
        sig_length = int(input_utxo[index2 + 2:index2 + 16], 16)
        index3 = index2 + 16

    # Get the signature
    index4 = index3 + sig_length * 2
    signature = input_utxo[index3:index4]

    # Finally get the sequence
    sequence = int(input_utxo[index4:index4 + UTXO_INPUT.SEQUENCE_BITS // 4], 16)

    # Create the utxo
    new_utxo = UTXO_INPUT(tx_id, tx_index, signature, sequence)

    # Verify the sig_length
    assert int(new_utxo.sig_length, 16) == sig_length

    # Return assembled utxo object
    return new_utxo


def decode_raw_output_utxo(output_utxo: str):
    '''
    The string will be hex chars and the BIT sizes that aren't variable are in the UTXO_OUTPUT class
    Divide bit size by 4 to get hex chars
    '''
    # Get amount val
    index1 = UTXO_OUTPUT.AMOUNT_BITS // 4
    amount = int(output_utxo[0:index1], 16)

    # Get variable length integer
    first_byte = int(output_utxo[index1:index1 + 2], 16)
    script_length = first_byte
    if first_byte < 253:
        index2 = index1 + 2
    elif first_byte == 253:
        script_length = int(output_utxo[index1 + 2:index1 + 4], 16)
        index2 = index1 + 4
    elif first_byte == 254:
        script_length = int(output_utxo[index1 + 2:index1 + 8], 16)
        index2 = index1 + 8
    else:
        assert first_byte == 255
        script_length = int(output_utxo[index1 + 2:index1 + 16], 16)
        index2 = index1 + 16

    # Get the locking script
    index3 = index2 + script_length * 2
    locking_script = output_utxo[index2: index3]

    # Create the utxo
    new_utxo = UTXO_OUTPUT(amount, locking_script)

    # Verify the script length
    assert int(new_utxo.script_length, 16) == script_length

    # Return utxo output object
    return new_utxo


'''
TESTING
'''
from hashlib import sha256
from wallet import Wallet


def test():
    w = Wallet()
    hash = sha256('hash'.encode()).hexdigest()
    sig = w.sign_transaction(hash)

    input1 = UTXO_INPUT(hash, 0, sig)
    locking_script = w.compressed_public_key
    output1 = UTXO_OUTPUT(10, locking_script)
    return output1
