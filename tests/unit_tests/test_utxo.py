'''
UTXO Testing
'''
import random
import string
from hashlib import sha256
from utxo import UTXO_INPUT, UTXO_OUTPUT, decode_raw_input_utxo, decode_raw_output_utxo
import secrets
from wallet import Wallet
import numpy as np


def test_raw_utxo():
    w = Wallet()
    random_string = ''
    for x in range(0, np.random.randint(100)):
        random_string += random.choice(string.ascii_letters)

    tx_id = sha256(random_string.encode()).hexdigest()
    tx_index = 0
    sig = w.sign_transaction(tx_id)
    utxo = UTXO_INPUT(tx_id, tx_index, sig)
    raw1 = utxo.raw_utxo
    utxo2 = decode_raw_input_utxo(raw1)

    assert utxo2.raw_utxo == raw1


def test_raw_output():
    amount = secrets.randbelow(1000)
    address = Wallet().address

    output1 = UTXO_OUTPUT(amount, address)
    raw1 = output1.raw_utxo
    output2 = decode_raw_output_utxo(raw1)

    assert output2.raw_utxo == raw1
