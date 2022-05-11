'''
The Transaction class

The Transaction will contain the following fields with assigned sizes:

Max byte size ~ 42kb
#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  type        |   8           |   2           |   1               |#
#|  input count |   8           |   2           |   1               |#
#|  inputs      |   var         |   var         |   max ~34kb       |#
#|  output count|   8           |   2           |   1               |#
#|  outputs     |   var         |   var         |   max ~8kb        |#
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
    TYPE_BITS = 8

    def __init__(self, inputs: list, outputs: list, version=1):
        '''
        A Transaction can be instantiated with a list of inputs - which will be a list of raw utxo_input values - and
        a list of outputs - which will be a list of raw utxo_output values. The minimum height represents the minimum
        block height in which that Transaction can be saved to the chain. If set to 0, it is valid to be accepted in
        any Block. This field will be used primarily by mining Transactions, in order to establish its validity. Version we fix to 1 for the time being.
        '''
        # Fix type
        self.type = format(1, f'0{self.TYPE_BITS // 4}x')

        # Format version and min_height
        self.version = format(version, f'0{self.VERSION_BITS // 4}x')

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

        return self.type + self.input_num + input_string + self.output_num + output_string + self.version

    @property
    def id(self):
        return sha256(self.raw_tx.encode()).hexdigest()


class GenesisTransaction:
    '''
    The Genesis Transaction for the Genesis Block.
    All values in the Genesis Block should be utilzed by the Blockchain - nothing else should be hardcoded except the values in the Genesis tx and Block
    '''

    '''
    FORMATTING BITS
    '''
    BITLENGTH_BITS = 16
    ACOEFF_BITS = 8
    BCOEFF_BITS = 8
    TARGET_BITS = 8
    PRIME_BITS = 256
    GENERATOR_COORD_BITS = 256
    GROUP_ORDER_BITS = 256
    MINE_AMOUNT_BITS = 64
    MINE_REWARD_BITS = 32

    '''
    ELLIPTIC CURVE VALUES
    '''
    a = 0
    b = 7
    p = pow(2, 256) - pow(2, 32) - pow(2, 9) - pow(2, 8) - pow(2, 7) - pow(2, 6) - pow(2, 4) - 1
    gx = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798
    gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8
    order = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141

    '''
    MINING VALUES
    '''
    AMOUNT_EXPONENT = 41
    REWARD_EXPONENT = 10
    STARTING_TARGET = 25

    '''
    
    '''

    def __init__(self, a_coeff=a, b_coeff=b, prime=p, generator_x=gx, generator_y=gy, group_order=order,
                 mine_amount=pow(2, AMOUNT_EXPONENT), reward=pow(2, REWARD_EXPONENT), target=STARTING_TARGET):
        # Fix type
        self.type = format(0, f'0{Transaction.TYPE_BITS // 4}x')

        # Format a and b coeff
        self.acoeff = format(a_coeff, f'0{self.ACOEFF_BITS // 4}x')
        self.bcoeff = format(b_coeff, f'0{self.BCOEFF_BITS // 4}x')

        # Format p
        self.prime = format(prime, f'0{self.PRIME_BITS // 4}x')

        # Format generator
        self.generator_x = format(generator_x, f'0{self.GENERATOR_COORD_BITS // 4}x')
        self.generator_y = format(generator_y, f'0{self.GENERATOR_COORD_BITS // 4}x')

        # Format order
        self.group_order = format(group_order, f'0{self.GROUP_ORDER_BITS // 4}x')

        # Create initial mining amount
        self.amount_to_mine = format(mine_amount, f'0{self.MINE_AMOUNT_BITS // 4}x')

        # Create initial mining reward
        self.starting_reward = format(reward, f'0{self.MINE_REWARD_BITS // 4}x')

        # Create initial starting target
        self.starting_target = format(target, f'0{self.TARGET_BITS // 4}x')

    @property
    def raw_tx(self):
        return self.type + self.acoeff + self.bcoeff + self.prime + self.generator_x + self.generator_y + self.group_order + self.amount_to_mine + self.starting_reward + self.starting_target

    @property
    def id(self):
        return sha256(self.raw_tx.encode()).hexdigest()


'''
Decoding
'''


def decode_raw_transaction(raw_tx: str):
    '''
    We decode the raw transaction using the raw_tx string and bit constants.
    '''
    # Get type
    type_index = Transaction.TYPE_BITS // 4
    type = int(raw_tx[:type_index], 16)

    if type == 0:
        # Set index vars
        acoeff_index = GenesisTransaction.ACOEFF_BITS // 4
        bcoeff_index = GenesisTransaction.BCOEFF_BITS // 4
        prime_index = GenesisTransaction.PRIME_BITS // 4
        generator_index = GenesisTransaction.GENERATOR_COORD_BITS // 4
        order_index = GenesisTransaction.GROUP_ORDER_BITS // 4
        mine_amount_index = GenesisTransaction.MINE_AMOUNT_BITS // 4
        reward_index = GenesisTransaction.MINE_REWARD_BITS // 4
        target_index = GenesisTransaction.TARGET_BITS // 4

        index1 = type_index
        index2 = index1 + acoeff_index
        index3 = index2 + bcoeff_index
        index4 = index3 + prime_index
        index5 = index4 + generator_index
        index6 = index5 + generator_index
        index7 = index6 + order_index
        index8 = index7 + mine_amount_index
        index9 = index8 + reward_index
        index10 = index9 + target_index

        a = int(raw_tx[index1:index2], 16)
        b = int(raw_tx[index2:index3], 16)
        p = int(raw_tx[index3:index4], 16)
        gx = int(raw_tx[index4:index5], 16)
        gy = int(raw_tx[index5:index6], 16)
        order = int(raw_tx[index6:index7], 16)
        mine_amount = int(raw_tx[index7:index8], 16)
        reward = int(raw_tx[index8:index9], 16)
        target = int(raw_tx[index9:index10], 16)

        return GenesisTransaction(a_coeff=a, b_coeff=b, prime=p, generator_x=gx, generator_y=gy, group_order=order,
                                  mine_amount=mine_amount, reward=reward, target=target)




    elif type == 2:
        pass
    else:

        # Set index variables
        count_index = Transaction.COUNT_BITS // 4
        version_index = Transaction.VERSION_BITS // 4

        # Get input num
        input_num = int(raw_tx[type_index:type_index + count_index], 16)

        # Get inputs
        inputs = []
        temp_index = type_index + count_index  # We use temp_index as the shifting string index throughout
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

        # Get version
        version = int(raw_tx[temp_index:temp_index + version_index], 16)

        return Transaction(inputs=inputs, outputs=outputs, version=version)
