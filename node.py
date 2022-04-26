'''
The Node class
'''

'''
IMPORTS
'''
from block import Block, decode_raw_block
from blockchain import Blockchain
from miner import Miner
from transaction import Transaction, decode_raw_transaction
from utxo import UTXO_OUTPUT
from wallet import Wallet
import threading

'''
CLASS
'''


class Node:
    '''

    '''

    def __init__(self, wallet=None):
        '''

        '''
        # Instantiate the Blockchain
        self.blockchain = Blockchain()

        # Create Miner
        self.miner = Miner()

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
            mining_transaction = Transaction(inputs=[], outputs=[mining_output.raw_utxo])
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
                self.add_block(mined_block.raw_block)
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
        self.blockchain.add_block(raw_block)
