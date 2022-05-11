'''
Testing elements of the blockchain
'''

'''
IMPORTS
'''
from blockchain import Blockchain
from miner import Miner
from transaction import Transaction
from utxo import UTXO_OUTPUT, UTXO_INPUT
import numpy as np
from wallet import Wallet
from block import Block, decode_raw_block

'''
GENESIS CONSTANTS
'''
###TARGET = 24###
# WALLET
GENESIS_WALLET_SEED = 274579355824125406041849328468268030210
GENESIS_ADDRESS = 'LsGSWuW7DxKoUhC5WXVhvLBiZRTxQTdAv'
# BLOCK
GENESIS_TIMESTAMP = 1651769733
GENESIS_NONCE = 52380188
GENESIS_ID = '0000000182ec0a016fe937342eaf96882eb4c91953e417bb4428c2f7101ba831'
GENSIS_TX_ID = '61928104f16552b4dd995b8c6014b6327ae046cf77e38bf3863bc51e0aa5a57d'
# SIGNATURE
GENESIS_SIGNATURE = '420213e322dc11b4f3778896bd72ca96fa79a0bd0a6c986e5057236ecb2bffd54b4c40279202d872ea89f0cbdbbfa3448031d9cb99a4b4efe913b61d8f313070e9badf407deca985023bcfb9634aaf088b8c095e3799d1b31f340c7b0a82b0d90c1d5a36'
##################

'''
TESTS
'''


def test_genesis_block():
    b = Blockchain()
    genesis_block = decode_raw_block(b.last_block)
    assert genesis_block.id == GENESIS_ID
    assert int(genesis_block.nonce, 16) == GENESIS_NONCE
    assert int(genesis_block.timestamp, 16) == GENESIS_TIMESTAMP

    t = genesis_block.transactions[0]

# def test_utxo_consumption():
#     b = Blockchain()
#     w = Wallet()
#     input_utxo = UTXO_INPUT(GENSIS_TX_ID, 0, GENESIS_SIGNATURE)
#     output_utxo = UTXO_OUTPUT(b.determine_reward(), w.address)
#     tx = Transaction(inputs=[input_utxo.raw_utxo], outputs=[output_utxo.raw_utxo])
#     unmined_block = Block(GENESIS_ID, b.determine_target(), 0, [tx.raw_tx])
#     m = Miner()
#     mined_raw_block = m.mine_block(unmined_block.raw_block)
#     assert b.add_block(mined_raw_block)
#
#     utxos = b.utxos
#     assert len(utxos) == 1
#     utxo_index = utxos.index[utxos['tx_id'] == tx.id]
#     assert utxos.loc[utxo_index]['address'].values[0] == w.address
#     consumed_index = utxos.index[utxos['tx_id'] == GENESIS_ID]
#     assert consumed_index.empty
#
#     assert b.pop_block()
#     assert not b.pop_block()
#     b2 = Blockchain()
#     assert b.utxos.equals(b2.utxos)
