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
    w = Wallet()
    reward = np.random.randint(40)
    target = 20
    output1 = UTXO_OUTPUT(reward, w.address)
    tx_1 = Transaction(inputs=[], outputs=[output1.raw_utxo], locktime=1)

    genesis_block = Block('', target, 0, [tx_1.raw_transaction])
    mined_genesis_raw = m.mine_block(genesis_block.raw_block)
    assert b.add_block(mined_genesis_raw)
    mined_genesis_block = decode_raw_block(mined_genesis_raw)
    tx_id = mined_genesis_block.tx_ids[0]
    tx_index = 0
    sig = w.sign_transaction(tx_id)
    input1 = UTXO_INPUT(tx_id, tx_index, sig)
    tx_2 = Transaction(inputs=[input1.raw_utxo], outputs=[], locktime=2)

    next_block = Block(mined_genesis_block.id, target, 0, [tx_2.raw_transaction])
    mined_next_raw = m.mine_block(next_block.raw_block)
    assert b.add_block(mined_next_raw)
    assert b.utxos.empty
