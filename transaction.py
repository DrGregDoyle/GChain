'''
The Transaction class

The Transaction will contain the following fields with assigned sizes:

Max byte size ~ 42kb
#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  input count |   8           |   2           |   1               |#
#|  inputs      |   var         |   var         |   max ~34kb       |#
#|  output count|   8           |   2           |   1               |#
#|  outputs     |   var         |   var         |   max ~8kb        |#
#|  min height  |   32          |   8           |   4               |#
#|  version     |   8           |   2           |   1               |#
#====================================================================#

'''
import random
import string

'''
IMPORTS
'''
from utxo import decode_raw_output_utxo, decode_raw_input_utxo, UTXO_INPUT, UTXO_OUTPUT
from hashlib import sha256

'''
TRANSACTION 
'''


class Transaction:
    '''

    '''
    COUNT_BITS = 8
    MIN_HEIGHT_BITS = 32
    VERSION_BITS = 8

    def __init__(self, inputs: list, outputs: list, min_height=0, version=1):
        '''
        A Transaction can be instantiated with a list of inputs - which will be a list of raw utxo_input values - and
        a list of outputs - which will be a list of raw utxo_output values. The minimum height represents the minimum
        block height in which that Transaction can be saved to the chain. If set to 0, it is valid to be accepted in
        any Block. This field will be used primarily by mining Transactions, in order to establish its validity. Version we fix to 1 for the time being.
        '''

        # Format version and min_height
        self.version = format(version, f'0{self.VERSION_BITS // 4}x')
        self.min_height = format(min_height, f'0{self.MIN_HEIGHT_BITS // 4}x')

        # Iterate over raw input utxo's and store the objects
        self.inputs = []
        for i in inputs:
            input_utxo = decode_raw_input_utxo(i)
            self.inputs.append(input_utxo)

        # Iterate over raw output utxo's and store the objects
        self.outputs = []
        for t in outputs:
            output_utxo = decode_raw_output_utxo(t)
            self.outputs.append(output_utxo)

        # Get hex string for counts
        self.input_num = format(len(self.inputs), f'0{self.COUNT_BITS // 4}x')
        self.output_num = format(len(self.outputs), f'0{self.COUNT_BITS // 4}x')

    '''
    PROPERTIES
    '''

    @property
    def raw_tx(self):
        input_string = ''
        output_string = ''

        for i in self.inputs:
            input_string += i.raw_utxo

        for t in self.outputs:
            output_string += t.raw_utxo

        return self.input_num + input_string + self.output_num + output_string + self.min_height + self.version

    @property
    def id(self):
        return sha256(self.raw_tx.encode()).hexdigest()

    @property
    def byte_size(self):
        return len(self.raw_tx) // 2


'''
Decoding
'''


def decode_raw_transaction(raw_tx: str) -> Transaction:
    '''
    We decode the raw transaction using the raw_tx string and bit constants.
    '''
    # Set index variables
    count_index = Transaction.COUNT_BITS // 4
    min_height_index = Transaction.MIN_HEIGHT_BITS // 4
    version_index = Transaction.VERSION_BITS // 4

    # Get input num
    input_num = int(raw_tx[:count_index], 16)

    # Get inputs
    inputs = []
    temp_index = count_index  # We use temp_index as the shifting string index throughout
    for x in range(0, input_num):
        raw_input_utxo = decode_raw_input_utxo(raw_tx[temp_index:]).raw_utxo
        inputs.append(raw_input_utxo)
        temp_index += len(raw_input_utxo)

    # Get output num
    output_num = int(raw_tx[temp_index: temp_index + count_index], 16)

    # Get outputs
    outputs = []
    temp_index += count_index
    for y in range(0, output_num):
        raw_output_utxo = decode_raw_output_utxo(raw_tx[temp_index:]).raw_utxo
        outputs.append(raw_output_utxo)
        temp_index += len(raw_output_utxo)

    # Get min height
    min_height = int(raw_tx[temp_index: temp_index + min_height_index], 16)
    temp_index += min_height_index

    # Get version
    version = int(raw_tx[temp_index:temp_index + version_index], 16)

    return Transaction(inputs=inputs, outputs=outputs, min_height=min_height, version=version)


'''
TESTING
'''
from wallet import Wallet
import numpy as np


def generate_transaction():
    '''
    We create a random number of inputs and outputs and create a Transaction from this.
    '''
    # Create inputs
    inputs = []
    input_num = 0
    while input_num == 0:
        input_num = np.random.randint(10)
    for x in range(0, input_num):
        random_string = ''
        for r in range(0, np.random.randint(100)):
            random_string += random.choice(string.ascii_letters)
        tx_id = sha256(random_string.encode()).hexdigest()
        tx_index = np.random.randint(100)
        sig = Wallet().sign_transaction(tx_id)
        inputs.append(UTXO_INPUT(tx_id, tx_index, sig).raw_utxo)

    # Create outputs
    outputs = []
    output_num = 0
    while output_num == 0:
        output_num = np.random.randint(10)
    for y in range(0, output_num):
        amount = np.random.randint(1000)
        temp_wallet = Wallet()
        address = temp_wallet.address
        utxo_output = UTXO_OUTPUT(amount, address)
        outputs.append(utxo_output.raw_utxo)

    return Transaction(inputs=inputs, outputs=outputs)
