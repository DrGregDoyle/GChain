'''
Testing the Block class
'''
import random
import secrets
import string
import numpy as np

from block import Block, utc_to_seconds, seconds_to_utc, decode_raw_block, decode_raw_block_transactions, \
    decode_raw_header, decode_raw_transaction
from transaction import generate_transaction
from hashlib import sha256
import datetime


def test_merkle_root():
    transactions = []
    for x in range(0, 3):
        transactions.append(generate_transaction().raw_transaction)

    test_block = Block('', 0, 0, transactions)

    tx_ids = test_block.tx_ids

    hash_ab = sha256((tx_ids[0] + tx_ids[1]).encode()).hexdigest()
    hash_cc = sha256((tx_ids[2] + tx_ids[2]).encode()).hexdigest()

    result_dict1 = test_block.merkle_proof(tx_ids[0])
    result_dict2 = test_block.merkle_proof(tx_ids[1])
    result_dict3 = test_block.merkle_proof(tx_ids[2])

    # 1st tx_id
    layer2_1 = result_dict1[0]
    layer1_1 = result_dict1[1]
    layer0_1 = result_dict1[2]

    assert layer2_1[2] == tx_ids[1]
    assert layer2_1['is_left'] == False
    assert layer1_1[1] == hash_cc
    assert layer1_1['is_left'] == False
    assert layer0_1[0] == test_block.merkle_root
    assert layer0_1['root_verified'] == True

    # 2nd tx_id
    layer2_2 = result_dict2[0]
    layer1_2 = result_dict2[1]
    layer0_2 = result_dict2[2]

    assert layer2_2[2] == tx_ids[0]
    assert layer2_2['is_left'] == True
    assert layer1_2[1] == hash_cc
    assert layer1_2['is_left'] == False
    assert layer0_2[0] == test_block.merkle_root
    assert layer0_2['root_verified'] == True

    # 3rd tx_id
    layer2_3 = result_dict3[0]
    layer1_3 = result_dict3[1]
    layer0_3 = result_dict3[2]

    assert layer2_3[2] == tx_ids[2]
    assert layer2_3['is_left'] == False
    assert layer1_3[1] == hash_ab
    assert layer1_3['is_left'] == True
    assert layer0_3[0] == test_block.merkle_root
    assert layer0_3['root_verified'] == True


def test_utc_converter():
    utc_now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    epoch_seconds = utc_to_seconds()
    now_string = seconds_to_utc(epoch_seconds) + '+00:00'
    assert utc_now == now_string


def test_encoding():
    transactions = []

    random_string = ''
    for x in range(0, np.random.randint(25)):
        random_string += random.choice(string.ascii_letters)
    tx_hash = sha256(random_string.encode()).hexdigest()

    random_num1 = secrets.randbelow(99999)
    random_num2 = secrets.randbelow(99999)
    random_num3 = secrets.randbelow(99999)

    for x in range(0, 3):
        transactions.append(generate_transaction().raw_transaction)

    new_block = Block(tx_hash, random_num2, random_num3, transactions, version=random_num1)
    raw_block = new_block.raw_block
    raw_header = new_block.raw_header
    raw_txs = new_block.raw_transactions

    decoded_block = decode_raw_block(raw_block)
    decoded_header = decode_raw_header(raw_header)
    decoded_txs = decode_raw_block_transactions(raw_txs)
    decoded_tx_ids = []
    for t in decoded_txs:
        decoded_tx_ids.append(decode_raw_transaction(t).id)

    assert decoded_block.raw_block == raw_block
    assert decoded_block.raw_header == raw_header
    assert decoded_block.raw_transactions == raw_txs
    assert decoded_header['version'] == random_num1
    assert decoded_header['target'] == random_num2
    assert decoded_header['nonce'] == random_num3
    assert decoded_tx_ids == new_block.tx_ids == decoded_block.tx_ids
