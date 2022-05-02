'''
The Transaction class

The Transaction will contain the following fields with assigned sizes:

#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  version     |   32          |   8           |   4               |#
#|  input count |   VLI         |   VLI         |   VLI             |#
#|  inputs      |   var         |   var         |   var             |#
#|  output count|   VLI         |   VLI         |   VLI             |#
#|  outputs     |   var         |   var         |   var             |#
#|  locktime    |   32          |   8           |   4               |#
#====================================================================#

TODO: Figure out where we verify that total input amount = total output amount
    -Will be done in the node when validating transactions
    -Will be done in the blockchain when validating transactions
'''
import random
import string

'''
IMPORTS
'''
from utxo import decode_raw_output_utxo, decode_raw_input_utxo, UTXO_INPUT, UTXO_OUTPUT
from vli import VLI
from hashlib import sha256
import secrets

'''
TRANSACTION 
'''


class Transaction:
    '''

    '''
    VERSION_BITS = 32
    LOCKTIME_BITS = 32

    def __init__(self, inputs: list, outputs: list, version=1, locktime=0):
        '''
        A Transaction can be instantiated with either a single output (representing a mining transaction) or a list of inputs and outputs.
        The elements of each of these lists will be raw utxos - a raw input utxo for an input and a raw output utxo for an output.
        When instantiated, the UTXOS will be stored as objects, for ease of use.


        '''

        # Format version and locktime
        self.version = format(version, f'0{self.VERSION_BITS // 4}x')
        self.locktime = format(locktime, f'0{self.LOCKTIME_BITS // 4}x')

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

        # Get VLI for input count
        input_count = len(self.inputs)
        self.input_num = VLI(input_count).vli_string

        # Get VLI for output count
        output_count = len(self.outputs)
        self.output_num = VLI(output_count).vli_string

    '''
    PROPERTIES
    '''

    @property
    def raw_transaction(self):
        input_string = ''
        output_string = ''

        for i in self.inputs:
            input_string += i.raw_utxo

        for t in self.outputs:
            output_string += t.raw_utxo

        return self.version + self.input_num + input_string + self.output_num + output_string + self.locktime

    @property
    def id(self):
        return sha256(self.raw_transaction.encode()).hexdigest()

    @property
    def byte_size(self):
        return len(self.raw_transaction) // 2

    @property
    def output_amount(self):
        total = 0
        for t in self.outputs:
            total += int(t.amount, 16)
        return total


'''
Decoding
'''


def decode_raw_transaction(raw_tx: str) -> Transaction:
    '''
    We decode the raw transaction using the raw_tx string and bit constants.
    '''

    # Get version
    index1 = Transaction.VERSION_BITS // 4
    version = int(raw_tx[0:index1], 16)

    # Get number of inputs
    first_byte_input = int(raw_tx[index1:index1 + 2], 16)
    temp_index_input = index1 + 2
    if first_byte_input < 253:
        input_num = first_byte_input
        index2 = temp_index_input
    else:
        index2 = temp_index_input + VLI.first_byte_index(first_byte_input)
        input_num = int(raw_tx[temp_index_input:index2], 16)

    # Get all inputs
    inputs = []
    for x in range(0, input_num):
        input_utxo = decode_raw_input_utxo(raw_tx[index2:])
        index2 += input_utxo.byte_size * 2
        inputs.append(input_utxo.raw_utxo)

    # Get number of outputs
    first_byte_output = int(raw_tx[index2:index2 + 2], 16)
    temp_index_output = index2 + 2
    if first_byte_output < 253:
        output_num = first_byte_output
        index3 = temp_index_output
    else:
        index3 = temp_index_output + VLI.first_byte_index(first_byte_output)
        output_num = int(raw_tx[temp_index_output:index3], 16)

    # Get all outputs
    outputs = []
    for x in range(0, output_num):
        output_utxo = decode_raw_output_utxo(raw_tx[index3:])
        index3 += output_utxo.byte_size * 2
        outputs.append(output_utxo.raw_utxo)

    # Get locktime
    locktime = int(raw_tx[index3: index3 + Transaction.LOCKTIME_BITS // 4], 16)

    # Create transaction
    new_transaction = Transaction(inputs=inputs, outputs=outputs, version=version, locktime=locktime)

    # Verify input and output num
    assert int(new_transaction.input_num, 16) == input_num
    assert int(new_transaction.output_num, 16) == output_num

    # Return transaction
    return new_transaction


'''
TESTING
'''
from wallet import Wallet
import numpy as np


def generate_transaction():
    '''
    We generate a random transaction
    '''

    # Generate a non-zero random number of inputs
    inputs = []
    input_num = 0
    while input_num == 0:
        input_num = np.random.randint(10)

    for i in range(0, input_num):
        w = Wallet()
        string_length = 0
        while string_length == 0:
            string_length = np.random.randint(256)
        random_string = ''
        for s in range(0, string_length):
            random_string += random.choice(string.ascii_letters)

        tx_id = sha256(random_string.encode()).hexdigest()
        index = secrets.randbelow(pow(2, 10))
        sig = w.sign_transaction(tx_id)
        input_utxo = UTXO_INPUT(tx_id, index, sig)
        inputs.append(input_utxo.raw_utxo)

    # Generate a non-zero random number of outputs
    outputs = []
    output_num = 0
    while output_num == 0:
        output_num = np.random.randint(10)

    for t in range(0, output_num):
        w1 = Wallet()
        amount = secrets.randbelow(pow(2, 20))
        output_utxo = UTXO_OUTPUT(amount, w1.address)
        outputs.append(output_utxo.raw_utxo)

    new_transaction = Transaction(inputs, outputs)
    return new_transaction
