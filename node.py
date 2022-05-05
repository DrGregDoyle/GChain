'''
The Node class

TODO: Add verifying that total input amount is greater than total output amount
TODO: Decide on less code vs more clarity in what's happening

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
from wallet import Wallet
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

    @property
    def curve(self):
        return self.blockchain.curve

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
            mining_amount = self.get_mining_amount()
            mining_output = UTXO_OUTPUT(mining_amount, self.wallet.address)
            current_height = self.blockchain.height
            mining_transaction = Transaction(inputs=[], outputs=[mining_output.raw_utxo], min_height=current_height + 1)
            self.validated_transactions.insert(0, mining_transaction.raw_tx)

            # Create candidate block
            if self.last_block == []:
                new_block = Block('', self.get_mining_target(), 0, self.validated_transactions)
            else:
                last_block = decode_raw_block(self.last_block)
                new_block = Block(last_block.id, self.get_mining_target(), 0, self.validated_transactions)

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

    def get_mining_amount(self):
        '''
        The mining reward will be the difference between the sum of all input amounts and the sum of all output
        amounts, plus the reward variable. We also verify that the total_input_amount >= total_output_amount and that
        the referenced output utxos for each input utxo exists.
        '''

        total_input_amount = 0
        total_output_amount = 0
        reward = self.get_mining_reward()

        for t in self.validated_transactions:
            # Recover tx
            temp_tx = decode_raw_transaction(t)

            # Add total input amount for tx
            for i in temp_tx.inputs:
                tx_id = i.tx_id
                tx_index = i.tx_index
                input_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]
                assert not input_index.empty
                total_input_amount += int(self.utxos.loc[input_index]['amount'].values[0], 16)

            # Add total output amount for tx
            for t in temp_tx.outputs:
                total_output_amount += int(t.amount, 16)

        assert total_input_amount >= total_output_amount
        return reward + (total_input_amount - total_output_amount)

    def get_mining_reward(self):
        return self.blockchain.determine_reward()

    def get_mining_target(self):
        '''
        Algorithm for determining mining target goes here
        '''
        return self.blockchain.determine_target()

    '''
    ADD BLOCK
    '''

    def add_block(self, raw_block: str):
        '''

        '''
        added = self.blockchain.add_block(raw_block)
        if added:
            self.check_for_parents()
        return added

    '''
    TRANSACTIONS
    '''

    def add_transaction(self, raw_tx: str) -> bool:
        '''
        When a Node receives a new transaction (tx), one of three things may happen: either the tx gets validated,
        in which case it's added to the validated transactions pool; or the tx has an invalid signature and locking
        script, in which case the tx is rejected; or the tx contains inputs which reference outputs which don't exist
        in the db, in which case this tx gets put in the orphaned transactions pool.

        We recover a Transaction object from the raw_tx string. We then iterate over all inputs. For each input,
        we first check that the referenced utxo output is stored in the blockchain. If the reference output does not
        exist, the Transaction gets flagged as orphaned. For the inputs whose reference utxo exists, we validate the
        input signature with the output locking script (compressed public key). If the signature fails validation,
        we reject the tx, otherwise we continue. As well, as we are validating each input tx, we are adding the value
        of the amount of the corresponding output utxo.

        Finally, if the transaction is not flagged as orphaned, we verify that the total input amount available in
        the output utxos stored in the blockchain is greater than or equal to the total output amount of the
        Transaction outputs. If the total input amount is smaller than the total output amount, we reject the tx.

        With the final check complete, either the tx is added to the validated tx pool or the orphaned tx pool,
        depending on the orphan flag.
        '''

        # Recover the transaction object
        new_tx = decode_raw_transaction(raw_tx)

        # Set orphaned transaction Flag
        all_inputs = True

        # Validate inputs
        total_input_amount = 0
        for i in new_tx.inputs:  # Looping over utxo_input objects

            # Get the row index for the output utxo
            tx_id = i.tx_id
            tx_index = int(i.tx_index, 16)
            input_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]

            # If the row doesn't exist, mark for orphan
            if input_index.empty:
                all_inputs = False

            # If the row exists, validate the input with the output and add the amount
            else:
                # Increase total_input_amount
                amount = int(self.utxos.loc[input_index]['amount'].values[0], 16)
                total_input_amount += amount

                # Validate the signature
                address = self.utxos.loc[input_index]['address'].values[0]
                if not self.blockchain.validate_signature(i.signature, address, tx_id):
                    return False

        # If not flagged for orphaned
        if all_inputs:
            # Get the total output amount
            total_output_amount = 0
            for t in new_tx.outputs:
                total_output_amount += int(t.amount, 16)

            # Verify the total output amount
            if total_output_amount > total_input_amount:
                return False

            # Add tx to validated tx pool
            self.validated_transactions.append(raw_tx)

        # Flagged for orphaned. Add to orphan pool
        else:
            self.orphaned_transactions.append(raw_tx)

        return True

    def check_for_parents(self):
        '''
        For every orphaned transaction, we see if its parents have arrived yet. If not, they will either be placed
        back in the orphaned tx pool, or invalidated.
        '''
        orphan_copies = self.orphaned_transactions.copy()
        self.orphaned_transactions = []
        for r in orphan_copies:
            self.add_transaction(r)

