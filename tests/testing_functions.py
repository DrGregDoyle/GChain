'''
FUNCTIONS FOR TESTING
'''
'''
IMPORTS
'''
import numpy as np
import random
from wallet import Wallet
import string
from hashlib import sha256
from utxo import UTXO_OUTPUT, UTXO_INPUT
from transaction import Transaction


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
