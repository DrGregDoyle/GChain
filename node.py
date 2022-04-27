'''
The Node class
'''
import random
import string

'''
IMPORTS
'''
from block import Block, decode_raw_block
from blockchain import Blockchain
from cryptography import EllipticCurve
from miner import Miner
from transaction import Transaction, decode_raw_transaction
from utxo import UTXO_OUTPUT, UTXO_INPUT, decode_raw_input_utxo, decode_raw_output_utxo
from wallet import Wallet, verify_signature, get_public_key_point
import threading
from hashlib import sha256
import numpy as np

'''
CLASS
'''


class Node:
    '''

    '''

    def __init__(self, wallet=None, a=None, b=None, p=None):
        '''

        '''
        # Instantiate the Blockchain
        self.blockchain = Blockchain()

        # Create Miner
        self.miner = Miner()

        # Create curve
        self.curve = EllipticCurve(a, b, p)

        # Create local wallet if none used during instantiation
        if wallet is None:
            self.wallet = Wallet()
        else:
            self.wallet = wallet

        # Create Mining and Listening flags
        self.is_mining = False
        self.is_listening = False

        # Create transaction lists
        self.incoming_transactions = []
        self.validated_transactions = []
        self.orphaned_transactions = []

    '''
    PROPERTIES
    '''

    @property
    def last_block(self):
        return self.blockchain.last_block

    @property
    def utxos(self):
        return self.blockchain.utxos

    '''
    MINER
    '''

    def start_miner(self):
        if not self.is_mining:
            self.is_mining = True
            self.mining_thread = threading.Thread(target=self.mine_block)
            self.mining_thread.start()
        else:
            # Logging
            print('Miner already running')

    def stop_miner(self):
        if self.is_mining:
            self.miner.stop_mining()
            while self.mining_thread.is_alive():
                pass
            self.is_mining = False
        else:
            # Logging
            print('Miner already stopped')

    def mine_block(self):
        interrupted = False
        while not interrupted:
            # Create Mining Transaction
            reward = self.get_mining_reward()
            locking_script = self.wallet.compressed_public_key
            mining_output = UTXO_OUTPUT(reward, locking_script)
            current_height = self.blockchain.height
            mining_transaction = Transaction(inputs=[], outputs=[mining_output.raw_utxo], locktime=current_height + 1)
            self.validated_transactions.insert(0, mining_transaction.raw_transaction)

            # Create candidate block
            if self.last_block == []:
                new_block = Block(1, '', self.get_mining_target(), 0, self.validated_transactions)
            else:
                last_block = decode_raw_block(self.last_block)
                new_block = Block(1, last_block.id, self.get_mining_target(), 0, self.validated_transactions)

            # print(f'Raw new block: {new_block.raw_block}')

            # Mine block
            mined_raw_block = self.miner.mine_block(new_block.raw_block)
            # Add block or interrupt miner
            if mined_raw_block != '':
                mined_block = decode_raw_block(mined_raw_block)
                added = self.add_block(mined_block.raw_block)
                if added:
                    self.validated_transactions = []
            else:
                # Remove mining transaction
                self.validated_transactions.pop(0)
                interrupted = True

        self.is_mining = False

    def get_mining_reward(self):
        '''
        Algorithm for determining mining reward goes here
        '''
        return 50

    def get_mining_target(self):
        '''
        Algorithm for determining mining target goes here
        '''
        return 20

    '''
    ADD BLOCK
    '''

    def add_block(self, raw_block: str):
        '''

        '''
        added = self.blockchain.add_block(raw_block)
        return added

    '''
    TRANSACTIONS
    '''

    def add_transaction(self, raw_tx: str):
        '''

        '''
        # Recover the transaction object
        new_tx = decode_raw_transaction(raw_tx)

        # Check that all output utxos exist for each input utxo
        all_inputs = True
        for i in new_tx.inputs:  # Looping over utxo_input objects
            tx_id = i.tx_id
            tx_index = int(i.tx_index, 16)
            input_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]
            if input_index.empty:  # If the row doesn't exist, mark for orphb
                all_inputs = False
            else:  # If the row exists, validate the input with the output
                locking_script = self.utxos.loc[input_index]['locking_script'].values[0]
                sig = i.signature
                pk_point = get_public_key_point(locking_script)
                valid = verify_signature(sig, tx_id, pk_point)
                if not valid:
                    return False

        if all_inputs:
            self.validated_transactions.append(raw_tx)
        else:
            self.orphaned_transactions.append(raw_tx)
        return True

    '''
    TESTING
    '''

    def generate_and_add_tx(self):
        random_string = ''
        for x in range(0, np.random.randint(50)):
            random_string += random.choice(string.ascii_letters)
        phantom_id = sha256(random_string.encode()).hexdigest()
        phantom_amount = np.random.randint(50)
        phantom_script = self.wallet.compressed_public_key
        self.blockchain.add_output_row(phantom_id, 0, phantom_amount, phantom_script)

        sig = self.wallet.sign_transaction(phantom_id)
        input_utxo = UTXO_INPUT(phantom_id, 0, sig)
        output_utxo = UTXO_OUTPUT(np.random.randint(50), phantom_script)

        tx = Transaction(inputs=[input_utxo.raw_utxo], outputs=[output_utxo.raw_utxo])
        self.add_transaction(tx.raw_transaction)
