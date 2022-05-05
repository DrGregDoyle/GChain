'''
The UTXO classes

We divide the UTXO into two classes: UTXO_INPUT, UTXO_OUTPUT.

The UTXO_INPUT has the following fields w corresponding size:   ~133 bytes
#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  tx_id       |   256         |   64          |   32              |#
#|  tx_index    |   8           |   2           |   1               |#
#|  sig length  |   8           |   2           |   1               |#
#|  signature*  |   ~800        |   ~200        |   ~100            |#
#====================================================================#


The UTXO_OUTPUT has the following fields w corresponding size: 33 bytes
#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  amount      |   64          |   16          |   8               |#
#|  addy length |   8           |   2           |   1               |#
#|  address     |   192         |   48          |   24              |#
#====================================================================#




'''
'''
IMPORTS
'''
from helpers import int_to_base58, base58_to_int


class UTXO_INPUT:
    '''

    '''
    TX_ID_BITS = 256
    TX_INDEX_BITS = 8

    def __init__(self, tx_id: str, tx_index: int, signature: str):
        # Format transaction id, index and sequence
        self.tx_id = tx_id
        if len(self.tx_id) != self.TX_ID_BITS // 4:
            self.tx_id = '0' + self.tx_id
        self.tx_index = format(tx_index, f'0{self.TX_INDEX_BITS // 4}x')

        # Get signature and signature length
        self.signature = signature
        self.sig_length = format(len(self.signature), '02x')

    '''
    Properties
    '''

    @property
    def raw_utxo(self):
        return self.tx_id + self.tx_index + self.sig_length + self.signature

    @property
    def byte_size(self):
        return len(self.raw_utxo) // 2


class UTXO_OUTPUT:
    '''
    The UTXO_OUTPUT object is instantiated by an integer amount and an address.
    The integer amount will be formatted and saved as hex string.
    The address is a BASE58 encoded CEPK, and we save both the address and the CEPK.
    The raw UTXO_OUTPUT object will then be CEPK appended to the formatted amount value.
    '''
    AMOUNT_BITS = 64

    def __init__(self, amount: int, address: str):
        # Format amount
        self.amount = format(amount, f'0{self.AMOUNT_BITS // 4}x')

        # Save BASE58 string address
        self.address = address

        # Get the cepk and addy_length
        self.cepk = hex(base58_to_int(self.address))[2:]
        self.addy_length = format(len(self.cepk), '02x')

    '''
    Properties
    '''

    @property
    def raw_utxo(self):
        return self.amount + self.addy_length + self.cepk

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

    i1 = UTXO_INPUT.TX_ID_BITS // 4
    i2 = i1 + UTXO_INPUT.TX_INDEX_BITS // 4
    i3 = i2 + 2
    tx_id = input_utxo[:i1]
    tx_index = int(input_utxo[i1:i2], 16)
    sig_length = int(input_utxo[i2:i3], 16)
    sig = input_utxo[i3:i3 + sig_length]

    return UTXO_INPUT(tx_id, tx_index, sig)


def decode_raw_output_utxo(output_utxo: str):
    '''
    The string will be hex chars and the BIT sizes that aren't variable are in the UTXO_OUTPUT class
    Divide bit size by 4 to get hex chars
    '''
    i1 = UTXO_OUTPUT.AMOUNT_BITS // 4
    i2 = i1 + 2

    amount = int(output_utxo[:i1], 16)
    addy_length = int(output_utxo[i1:i2], 16)
    address = int_to_base58(int(output_utxo[i2:i2 + addy_length], 16))

    return UTXO_OUTPUT(amount, address)
