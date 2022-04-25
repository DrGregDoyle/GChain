'''
The Transaction class

The Transaction will contain the following fields with assigned sizes:

#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  version     |   32          |   8           |   4               |#
#|  input count |   VLI         |   VLI         |   VLI             |#
#|  inputs      |   var         |   var         |   var             |#
#|  output count|   VLI         |   VLI         |   VLI             |#
#|  outputs     |   var         |   var         |   var             |#
#|  locktime    |   32          |   8           |   4               |#


'''
import random
import string

'''
IMPORTS
'''
from utxo import decode_raw_output_utxo, decode_raw_input_utxo, UTXO_INPUT, UTXO_OUTPUT
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
        The inputs and outputs will be lists of raw utxos
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
        if input_count < pow(2, 8) - 3:
            self.input_num = format(input_count, '02x')
        elif pow(2, 8) - 3 <= input_count <= pow(2, 16):
            self.input_num = 'FD' + format(input_count, '04x')
        elif pow(2, 16) < input_count <= pow(2, 32):
            self.input_num = 'FE' + format(input_count, '08x')
        else:
            self.input_num = 'FF' + format(input_count, '016x')

        # Get VLI for output count
        output_count = len(self.outputs)
        if output_count < pow(2, 8) - 3:
            self.output_num = format(output_count, '02x')
        elif pow(2, 8) - 3 <= output_count <= pow(2, 16):
            self.output_num = 'FD' + format(output_count, '04x')
        elif pow(2, 16) < output_count <= pow(2, 32):
            self.output_num = 'FE' + format(output_count, '08x')
        else:
            self.output_num = 'FF' + format(output_count, '016x')

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


'''
Decoding
'''


def decode_raw_transaction(raw_tx: str):
    '''
    We decode the raw transaction using the raw_tx string and bit constants.
    '''

    # Get version
    index1 = Transaction.VERSION_BITS // 4
    version = int(raw_tx[0:index1], 16)

    # Get number of inputs
    first_byte = int(raw_tx[index1:index1 + 2], 16)
    input_num = first_byte
    if first_byte < 253:
        index2 = index1 + 2
    elif first_byte == 253:
        input_num = int(raw_tx[index1 + 2:index1 + 4])
        index2 = index1 + 4
    elif first_byte == 254:
        input_num = int(raw_tx[index1 + 2:index1 + 8])
        index2 = index1 + 8
    else:
        assert first_byte == 255
        input_num = int(raw_tx[index1 + 2:index1 + 16])
        index2 = index1 + 16

    # Get all inputs
    inputs = []
    for x in range(0, input_num):
        input_utxo = decode_raw_input_utxo(raw_tx[index2:])
        index2 += input_utxo.byte_size * 2
        inputs.append(input_utxo.raw_utxo)

    # Get number of outputs
    first_byte_output = int(raw_tx[index2:index2 + 2], 16)
    output_num = first_byte_output
    if first_byte_output < 253:
        index3 = index2 + 2
    elif first_byte_output == 253:
        output_num = int(raw_tx[index1 + 2:index1 + 4])
        index3 = index2 + 4
    elif first_byte_output == 254:
        output_num = int(raw_tx[index1 + 2:index1 + 8])
        index3 = index2 + 8
    else:
        assert first_byte_output == 255
        output_num = int(raw_tx[index1 + 2:index1 + 16])
        index3 = index2 + 16

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


def generate_transaction():
    '''
    We generate a random transaction
    '''
    w1 = Wallet()

    amount = secrets.randbelow(pow(2, 20))
    output_utxo1 = UTXO_OUTPUT(amount, w1.compressed_public_key)

    random_string = random.choice(string.ascii_letters)

    tx_id = sha256(random_string.encode()).hexdigest()
    index = secrets.randbelow(pow(2, 10))
    sig = w1.sign_transaction(tx_id)
    input_utxo1 = UTXO_INPUT(tx_id, index, sig)

    new_transaction = Transaction([input_utxo1.raw_utxo], [output_utxo1.raw_utxo])
    return new_transaction

