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
GENESIS_NONCE = 28911710
GENESIS_ID = '00000008923c8a7549f38ea9f29240e387abb78523a0ca018ee91395007c83aa'
GENSIS_TX_ID = '4656133449a1bd4c7b6f785a244c0f6a9383319c1d7cbb9916c3ee7d518282c7'
# SIGNATURE
GENESIS_SIGNATURE = '420213e322dc11b4f3778896bd72ca96fa79a0bd0a6c986e5057236ecb2bffd54b4c404b103f51fc6b353d3dca37d67beb520e0c5b5262147c3337941e02b482a0294e401e950af744b8fea8ad6ab0a26f412eb338b2c2b73041177d05239a6b8babde3d'
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
