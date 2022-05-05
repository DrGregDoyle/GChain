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


def test_input_utxos():
    '''
    Verifying that an existing input utxo gets consumed
    '''
    b = Blockchain()
    m = Miner()
    w1 = Wallet()
    w2 = Wallet()
    reward = b.determine_reward()
    target = 20
    mining_output = UTXO_OUTPUT(reward, w1.address)
    mining_transaction = Transaction(inputs=[], outputs=[mining_output.raw_utxo])
    genesis_block = Block('', target, 0, [mining_transaction.raw_tx])
    mined_genesis_raw = m.mine_block(genesis_block.raw_block)
    assert b.add_block(mined_genesis_raw)
    saved_block = decode_raw_block(b.last_block)
    assert saved_block.raw_block == mined_genesis_raw

    utxo_input1 = UTXO_INPUT(mining_transaction.id, 0, w1.sign_transaction(mining_transaction.id))
    utxo_output1 = UTXO_OUTPUT(reward // 2, w2.address)
    utxo_output2 = UTXO_OUTPUT(reward // 2, w1.address)

    tx1 = Transaction(inputs=[utxo_input1.raw_utxo], outputs=[utxo_output1.raw_utxo, utxo_output2.raw_utxo])
    next_block = Block(saved_block.id, target, 0, [mining_transaction.raw_tx, tx1.raw_tx])
    mined_next_block_raw = m.mine_block(next_block.raw_block)
    assert b.add_block(mined_next_block_raw)
