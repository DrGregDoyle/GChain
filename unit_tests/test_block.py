'''
Testing the Block class
'''

from block import Block
from transaction import generate_transaction
from hashlib import sha256


def test_merkle_root():
    transactions = []
    for x in range(0, 3):
        transactions.append(generate_transaction().raw_transaction)

    test_block = Block(0, '', 0, 0, transactions)

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
