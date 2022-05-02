'''
The UTXO classes

We divide the UTXO into two classes: UTXO_INPUT, UTXO_OUTPUT.

The UTXO_INPUT has the following fields w corresponding size:
#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  tx_id       |   256         |   64          |   32              |#
#|  tx_index    |   32          |   8           |   4               |#
#|  sig_length  |   VLI         |   VLI         |   VLI             |#
#|  signature   |   var         |   var         |   var             |#
#|  sequence    |   32          |   8           |   4               |#
#====================================================================#


The UTXO_OUTPUT has the following fields w corresponding size:
#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  amount      |   32          |   8           |   4               |#
#|  addy_len    |   VLI         |   VLI         |   VLI             |#
#|  address     |   var         |   var         |   var             |#
#====================================================================#


NB: Both sig_length and unlock_len will be the length in BYTES

'''
'''
IMPORTS
'''
from vli import VLI
from wallet import Wallet
from helpers import int_to_base58, base58_to_int


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
        self.sig_length = VLI(byte_length).vli_string

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

    def __init__(self, amount: int, address: str):
        # Format amount
        self.amount = format(amount, f'0{self.AMOUNT_BITS // 4}x')

        # Save address as hex value
        self.hex_address = hex(base58_to_int(address))[2:]

        # Use variable length integer for byte length of signature
        byte_length = len(self.hex_address) // 2
        self.script_length = VLI(byte_length).vli_string

    '''
    Properties
    '''

    @property
    def raw_utxo(self):
        return self.amount + self.script_length + self.hex_address

    @property
    def byte_size(self):
        return len(self.raw_utxo) // 2

    @property
    def address(self):
        return int_to_base58(int(self.hex_address, 16))


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
    temp_index = index2 + 2
    if first_byte < 253:
        sig_length = first_byte
        index3 = temp_index
    else:
        index3 = temp_index + VLI.first_byte_index(first_byte)
        sig_length = int(input_utxo[temp_index:index3], 16)

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
    temp_index = index1 + 2
    if first_byte < 253:
        script_length = first_byte
        index2 = temp_index
    else:
        index2 = temp_index + VLI.first_byte_index(first_byte)
        script_length = int(output_utxo[temp_index:index2], 16)

    # Get the locking script
    index3 = index2 + script_length * 2
    hex_address = output_utxo[index2: index3]

    # Create the utxo
    new_utxo = UTXO_OUTPUT(amount, int_to_base58(int(hex_address, 16)))

    # Verify the script length
    assert int(new_utxo.script_length, 16) == script_length

    # Return utxo output object
    return new_utxo
