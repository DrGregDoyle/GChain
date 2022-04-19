'''
The transaction class


Bits    | Bytes     | Hex chars     | Field
-------------------------------------------
32      | 4         | 8             | Version
64      | 8         | 16            | Input count
var     | var       | var           | All inputs
64      | 8         | 16            | Output count
var     | var       | var           | All outputs
32      | 4         | 8             | Locktime


#TODO: Get variable length integer working for input/output count


'''

'''Imports'''
from utxo import UTXO, OUTPUT_UTXO, decode_raw_output, decode_raw_utxo
from hashlib import sha256
import secrets


class Transaction:
    VERSION_BYTES = 4
    INPUT_NUM_BYTES = 8
    OUTPUT_NUM_BYTES = 8
    LOCKTIME_BYTES = 4

    def __init__(self, version: int, input_count: int, inputs: list, output_count: int, outputs: list, locktime=0):
        '''
        We create the transaction
        '''

        self.version = format(version, f'0{2 * self.VERSION_BYTES}x')
        self.input_count = format(input_count, f'0{2 * self.INPUT_NUM_BYTES}x')
        self.inputs = inputs
        self.output_count = format(output_count, f'0{2 * self.OUTPUT_NUM_BYTES}x')
        self.outputs = outputs
        self.locktime = format(locktime, f'0{2 * self.LOCKTIME_BYTES}x')

    def get_raw_transaction(self):
        '''
        Output the concatenated hex strings of the unsigned transaction
        '''
        input_string = ''
        for i in self.inputs:
            input_string += i

        output_string = ''
        for t in self.outputs:
            output_string += t

        return self.version + self.input_count + input_string + self.output_count + output_string + self.locktime


'''
Decoding
'''


def decode_raw_transaction(raw_tx: str, VERSION_BYTES=4, INPUT_NUM_BYTES=8, OUTPUT_NUM_BYTES=8, LOCKTIME_BYTES=4):
    '''
    We decode the raw transaction using the raw_tx string and byte constants
    '''
    index1 = 2 * VERSION_BYTES
    index2 = index1 + 2 * INPUT_NUM_BYTES

    version = int(raw_tx[0:index1], 16)
    input_count = int(raw_tx[index1:index2], 16)

    temp_index_input = index2
    inputs = []
    for x in range(0, input_count):
        test_utxo = decode_raw_utxo(raw_tx[temp_index_input:])
        inputs.append(test_utxo.get_raw_utxo())
        temp_index_input = temp_index_input + test_utxo.get_hex_chars()

    index3 = temp_index_input
    index4 = index3 + 2 * OUTPUT_NUM_BYTES
    output_count = int(raw_tx[index3:index4], 16)

    temp_index_output = index4
    outputs = []
    for x in range(0, output_count):
        output_utxo = decode_raw_output(raw_tx[temp_index_output:])
        outputs.append(output_utxo.get_raw_output())
        temp_index_output = temp_index_output + output_utxo.get_hex_chars()

    index5 = temp_index_output
    index6 = index5 + 2 * LOCKTIME_BYTES
    locktime = int(raw_tx[index5:index6], 16)

    '''Verify that we've reached the end of the transaction'''
    assert len(raw_tx) == index6

    return Transaction(version, input_count, inputs, output_count, outputs, locktime)


'''
TESTING
'''


def test():
    tx_id = sha256('Transaction'.encode()).hexdigest()
    tx_index = 0
    sig_script = hex(secrets.randbits(288))[2:]
    sequence = 0xffffffff
    input_utxo = UTXO(tx_id, tx_index, sig_script, sequence)

    tx_index2 = 1
    sig_script2 = hex(secrets.randbits(140))[2:]
    input_utxo2 = UTXO(tx_id, tx_index2, sig_script2, sequence)

    amount = secrets.randbelow(1000)
    unlock_script = hex(secrets.randbits(360))[2:]
    output_utxo = OUTPUT_UTXO(amount, unlock_script)

    amount2 = secrets.randbelow(4000)
    unlock_script2 = hex(secrets.randbits(155))[2:]
    output_utxo2 = OUTPUT_UTXO(amount2, unlock_script2)

    version = 1
    input_count = 2
    inputs = [input_utxo.get_raw_utxo(), input_utxo2.get_raw_utxo()]
    output_count = 2
    outputs = [output_utxo.get_raw_output(), output_utxo2.get_raw_output()]

    t = Transaction(version, input_count, inputs, output_count, outputs)
    return t
