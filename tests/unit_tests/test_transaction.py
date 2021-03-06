'''
Testing transactions
'''
import random
import string
import numpy as np
from transaction import Transaction, decode_raw_transaction, GenesisTransaction, MiningTransaction
from utxo import UTXO_OUTPUT, UTXO_INPUT
import secrets
from hashlib import sha256
from wallet import Wallet


def test_raw_transaction():
    w1 = Wallet()
    w2 = Wallet()
    w3 = Wallet()
    w4 = Wallet()
    random_string_1 = ''
    random_string_2 = ''
    for x in range(0, np.random.randint(100)):
        random_string_1 += random.choice(string.ascii_letters)
    for x in range(0, np.random.randint(100)):
        random_string_2 += random.choice(string.ascii_letters)

    tx_id1 = sha256(random_string_1.encode()).hexdigest()
    tx_index1 = 0
    sig1 = w1.sign_transaction(tx_id1)
    input_utxo1 = UTXO_INPUT(tx_id1, tx_index1, sig1)

    tx_id2 = sha256(random_string_2.encode()).hexdigest()
    tx_index2 = 1
    sig2 = w2.sign_transaction(tx_id2)
    input_utxo2 = UTXO_INPUT(tx_id2, tx_index2, sig2)

    output_utxo1 = UTXO_OUTPUT(secrets.randbelow(1000), w3.address)
    output_utxo2 = UTXO_OUTPUT(secrets.randbelow(1000), w4.address)

    inputs = [input_utxo1.raw_utxo, input_utxo2.raw_utxo]
    outputs = [output_utxo1.raw_utxo, output_utxo2.raw_utxo]

    t = Transaction(inputs=inputs, outputs=outputs)
    raw = t.raw_tx
    new_t = decode_raw_transaction(raw)

    assert new_t.raw_tx == raw
    assert new_t.id == t.id


def test_genesis_transaction():
    g = GenesisTransaction()
    g1 = decode_raw_transaction(g.raw_tx)
    assert g.raw_tx == g1.raw_tx


def test_mining_transaction():
    random_height = secrets.randbits(64)
    random_reward = secrets.randbits(32)

    w = Wallet()
    output1 = UTXO_OUTPUT(secrets.randbelow(1000), w.address)
    mt1 = MiningTransaction(random_height, random_reward, output1.raw_utxo)
    mt2 = decode_raw_transaction(mt1.raw_tx)

    assert mt1.raw_tx == mt2.raw_tx
    assert int(mt2.height, 16) == random_height
    assert int(mt2.reward, 16) == random_reward