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
GENESIS_ADDRESS = 'HoKkFxMKyRTeuawTnZgRTurgGLcxgYBdo'
GENESIS_TIMESTAMP = 1651769733
GENESIS_NONCE = 1221286
GENESIS_ID = '0000080c2646139bb57558a650c0fcee8b0aceda034ae199b2cc6051abd81ee1'
GENESIS_SIGNATURE = '4203bbb4f439d5f7cd3507e8f780d1ad51ea29a3bd092e88814cacedf6877072eb284023c31f713e6a80e9ff2540e8bbe55d851b6056e42bfe2d45f44091f1a98419713f37131ff32388ffdeb085cb86b76f857d9ddeb1f3f1fb758a69c997de1d12e32'
GENSIS_TX_ID = 'fc4e1d257740ddb6a155bea28a0782b75b385b6028fe3f2d75bdd497fcb3d265'

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
    assert t.inputs == []

    output = t.outputs[0]
    assert output.address == GENESIS_ADDRESS


def test_utxo_consumption():
    b = Blockchain()
    w = Wallet()
    input_utxo = UTXO_INPUT(GENSIS_TX_ID, 0, GENESIS_SIGNATURE)
    output_utxo = UTXO_OUTPUT(b.determine_reward(), w.address)
    tx = Transaction(inputs=[input_utxo.raw_utxo], outputs=[output_utxo.raw_utxo])
    unmined_block = Block(GENESIS_ID, b.determine_target(), 0, [tx.raw_tx])
    m = Miner()
    mined_raw_block = m.mine_block(unmined_block.raw_block)
    assert b.add_block(mined_raw_block)

    utxos = b.utxos
    assert len(utxos) == 1
    utxo_index = utxos.index[utxos['tx_id'] == tx.id]
    assert utxos.loc[utxo_index]['address'].values[0] == w.address
    consumed_index = utxos.index[utxos['tx_id'] == GENESIS_ID]
    assert consumed_index.empty

    assert b.pop_block()
    assert not b.pop_block()
    b2 = Blockchain()
    assert b.utxos.equals(b2.utxos)
