'''
The Blockchain class
=====

The Blockchain will be the data structure which grows due to emergent consensus of the nodes. Each Node will contain
a copy of the Blockchain. When new Blocks are added, consensus is reached with available nodes through the consensus
algorithm.

The Blockchain will contain a list of raw Blocks, as well as the output UTXO pool. When a new Block is saved to the
Blockchain, the corresponding output UTXOs are consumed by the input in order to generate the new output UTXOs. It
may happen that a Block gets removed due to consensus algorithm, in which case the consumed output UTXOs will be
restored.

The Blockchain will contain the fixed curve parameters used for the address and locking script.

'''

'''
IMPORTS
'''

from block import decode_raw_block, Block
from cryptography import EllipticCurve
from hashlib import sha256, sha1
from helpers import get_signature_parts, int_to_base58, utc_to_seconds
from transaction import Transaction, decode_raw_transaction, GenesisTransaction
from utxo import UTXO_INPUT, UTXO_OUTPUT
from miner import Miner

import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

'''
CLASS
'''


class Blockchain:
    '''

    '''
    COLUMNS = ['tx_id', 'tx_index', 'amount', 'address']
    ADDRESS_CHECKSUM_BITS = 32

    '''
    GENESIS CONSTANTS
    '''
    GENESIS_ID = '0000000182ec0a016fe937342eaf96882eb4c91953e417bb4428c2f7101ba831'
    GENESIS_TIMESTAMP = 1651769733
    GENESIS_NONCE = 52380188

    def __init__(self):
        '''

        '''
        # Instantiate a blank chain
        self.chain = []

        # Create an empty utxo pool
        self.utxos = pd.DataFrame(columns=self.COLUMNS)

        # Generate genesis block
        ##LOGGING
        print('Creating genesis block in Blockchain. This may take a moment.')
        self.create_genesis_block()
        # Get Genesis TX values
        genesis_block = decode_raw_block(self.last_block)
        genesis_tx = genesis_block.transactions[0]

        # Get curve parameters
        self.a = int(genesis_tx.acoeff, 16)
        self.b = int(genesis_tx.bcoeff, 16)
        self.p = int(genesis_tx.prime, 16)
        self.generator = (int(genesis_tx.generator_x, 16), int(genesis_tx.generator_y, 16))
        self.group_order = int(genesis_tx.group_order, 16)

        # Instantiate curve
        self.curve = EllipticCurve(a=self.a, b=self.b, p=self.p, generator=self.generator, order=self.group_order)

        # Get mining values
        self.total_mining_amount = int(genesis_tx.amount_to_mine, 16)
        self.target = int(genesis_tx.starting_target, 16)
        self.reward = int(genesis_tx.starting_reward, 16)

        # Get heartbeat
        self.heartbeat = int(genesis_tx.heartbeat, 16)
        self.last_breath = utc_to_seconds()

    '''
    PROPERTIES
    '''

    @property
    def last_block(self):
        return self.chain[-1]

    @property
    def height(self):
        return len(self.chain) - 1

    '''
    VERIFY SIGNATURE
    '''

    def check_address(self, compressed_public_key: str, address: str) -> bool:
        '''
        If we take the "Address Generating" steps with the compressed public key and end up with the given address, we return True.
        Otherwise return False.
        '''

        # 1) Get sha1(sha256(compressed_public_key)) value
        raw_addy = sha1(sha256(compressed_public_key.encode()).hexdigest().encode()).hexdigest()

        # 2) Get checksum
        checksum = sha256(sha256(raw_addy.encode()).hexdigest().encode()).hexdigest()[: self.ADDRESS_CHECKSUM_BITS // 4]

        # 3) Return True/False
        return int_to_base58(int(raw_addy + checksum, 16)) == address

    def validate_signature(self, input_sig: str, output_addy: str, tx_id: str) -> bool:
        '''
        Given the signature in the input utxo and the address in the output utxo, we validate the signature.
        '''

        # Read in signature
        compressed_public_key, (r_hex, s_hex) = get_signature_parts(input_sig)

        # Validate address
        if not self.check_address(compressed_public_key, output_addy):
            # Logging
            print('Address error')
            return False

        # Get public key point, r and s
        pk_point = self.curve.get_public_key_point(compressed_public_key)
        r = int(r_hex, 16)
        s = int(s_hex, 16)

        # Validate signature. Return True/False
        return self.curve.verify_signature((r, s), tx_id, pk_point)

    '''
    DETERMINE MINING PROPERTIES
    '''

    def determine_heartbeat(self):
        '''
        '''
        return utc_to_seconds() - self.last_breath

    def determine_reward(self):
        '''
        Will determine a reward for miners based on the state of the chain
        '''
        return self.reward

    def determine_target(self):
        '''
        We adjust the target up or down based on the heartbeat
        '''
        heartrate = self.determine_heartbeat()
        if heartrate > self.heartbeat:  # Too slow
            self.target -= 1
        elif heartrate < self.heartbeat:  # Too fast - bigger issue than too slow
            self.target += 2

    '''
    CONSUME UTXO INPUTS
    '''

    def consume_input(self, utxo_input: UTXO_INPUT):
        '''
        We consume the corresponding utxo output for a given utxo input.
        WE DO NO VALIDATION AS THIS IS ONLY CALLED AFTER ALL BLOCK VALIDATION IS DONE
        '''

        tx_id = utxo_input.tx_id
        tx_index = int(utxo_input.tx_index, 16)
        output_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]
        self.utxos = self.utxos.drop(self.utxos.index[output_index])

    '''
    ADD BLOCK
    '''

    def add_block(self, raw_block: str) -> bool:
        '''

        '''
        # Decode raw block
        candidate_block = decode_raw_block(raw_block)

        # Verify target
        target = pow(2, 256 - int(candidate_block.target, 16))
        if int(candidate_block.id, 16) > target:
            # Logging:
            print('Target error in block')
            return False

        # Verify block header values
        last_block = decode_raw_block(self.last_block)
        if last_block.id != candidate_block.prev_hash:
            # Logging
            print('Previous hash error in block')
            return False

        # Consumed UTXO trackers
        consumed_inputs = []

        # Output UTXO temp dataframe
        output_utxo_df = pd.DataFrame(columns=self.COLUMNS)

        # Iterate over Transactions
        tx_count = 1
        for tx_object in candidate_block.transactions:

            # Verify type
            if tx_object.type == '02':
                # Verify height of mined block
                if int(tx_object.height, 16) != self.height + 1:
                    # Logging
                    print('Height error in block')
                    return False

                # # Verify reward
                # if int(tx_object.reward, 16) != self.determine_reward():
                #     # Logging
                #     print('Reward error in block')
                #     return False

                # Verify mining amount
                if int(tx_object.reward, 16) > self.total_mining_amount:
                    # Logging
                    print('Reward exceeds total mining amount')
                    return False

                # Deduct reward from total_mining_amount
                self.total_mining_amount -= int(tx_object.reward, 16)

                # Add output utxo - mining tx always has 0 index
                output_row = pd.DataFrame(
                    [[tx_object.id, 0, tx_object.mining_output.amount, tx_object.mining_output.address]],
                    columns=self.COLUMNS)
                output_utxo_df = pd.concat([output_utxo_df, output_row], ignore_index=True)
            else:
                # Validate the inputs.
                for i in tx_object.inputs:
                    # Get output UTXO identifying values
                    tx_id = i.tx_id
                    tx_index = int(i.tx_index, 16)

                    # Check that output utxo exists, return False if not
                    output_index = self.utxos.index[
                        (self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]
                    if output_index.empty:
                        # Logging
                        print('Empty output index error')
                        return False

                    # Validate the input utxo signature against the output utxo address
                    output_address = self.utxos.loc[output_index]['address'].values[0]

                    if not self.validate_signature(i.signature, output_address, tx_id, ):
                        # Logging
                        print('Validate signature error')
                        return False

                    # Scheduled input for consumption after all validation done
                    consumed_inputs.append(i)

                # Add the new outputs. Use count for the index

                for output_utxo in tx_object.outputs:
                    output_row = pd.DataFrame([[tx_object.id, tx_count, output_utxo.amount, output_utxo.address]],
                                              columns=self.COLUMNS)
                    output_utxo_df = pd.concat([output_utxo_df, output_row], ignore_index=True)
                    tx_count += 1

        ##ALL VALIDATION COMPLETE##
        # Consume the inputs
        for c in consumed_inputs:
            self.consume_input(c)

        # Add new outputs
        self.utxos = pd.concat([self.utxos, output_utxo_df], ignore_index=True)

        # Add Block
        self.chain.append(candidate_block.raw_block)

        # Adjust target
        self.determine_target()

        # Adjust reward
        self.determine_reward()

        # Adjust breathing rate
        self.last_breath = utc_to_seconds()

        return True

    '''
    POP BLOCK
    '''

    def pop_block(self) -> bool:
        '''
        This will remove the top most block in the chain.
        We reverse the utxo's in the block.
        '''
        # Don't pop the genesis block
        if self.height == 0:
            return False

        # Remove top most block
        removed_block = decode_raw_block(self.chain.pop(-1))

        # For each transaction, we remove the output utxos from the db and restore the related inputs
        for tx in removed_block.transactions:

            id = tx.id
            output_count = 1
            type = tx.type

            # Reverse mining tx
            if type == '02':
                output_index = self.utxos.index[(self.utxos['tx_id'] == id) & (self.utxos['tx_index'] == 0)]
                try:
                    assert not output_index.empty, 'Pop block error for mining tx, output utxo already consumed'
                except AssertionError as msg:
                    # Logging
                    print(msg)
                    return False
                self.total_mining_amount += int(tx.reward, 16)
                self.utxos = self.utxos.drop(self.utxos.index[output_index])
            else:
                # Drop all utxo outputs
                for t in tx.outputs:
                    output_index = self.utxos.index[
                        (self.utxos['tx_id'] == id) & (self.utxos['tx_index'] == output_count)]
                    try:
                        assert not output_index.empty, 'Pop block error, output utxo already consumed'
                    except AssertionError as msg:
                        # Logging
                        print(msg)
                        return False
                    self.utxos = self.utxos.drop(self.utxos.index[output_index])
                    output_count += 1

                # Restore all outputs for the inputs
                for i in tx.inputs:
                    tx_id = i.tx_id
                    tx_index = int(i.tx_index, 16)
                    raw_tx = ''
                    count = 0
                    while raw_tx == '':
                        temp_block = decode_raw_block(self.chain[count])
                        raw_tx = temp_block.get_raw_tx(tx_id)
                        count += 1
                    temp_tx = decode_raw_transaction(raw_tx)
                    temp_output = temp_tx.outputs[tx_index]
                    temp_amount = temp_output.amount
                    temp_address = temp_output.address
                    row = pd.DataFrame([[tx_id, tx_index, temp_amount, temp_address]], columns=self.COLUMNS)
                    self.utxos = pd.concat([self.utxos, row], ignore_index=True)

        return True

    '''
    GENESIS BLOCK
    '''

    def create_genesis_block(self):
        # output_utxo = UTXO_OUTPUT(self.determine_reward(), self.GENESIS_ADDRESS)
        # genesis_tx = Transaction(inputs=[], outputs=[output_utxo.raw_utxo])
        genesis_tx = GenesisTransaction()
        target = int(genesis_tx.starting_target, 16)
        genesis_block = Block('', target, 0, [genesis_tx.raw_tx], self.GENESIS_TIMESTAMP)

        # Mine Block to calculate initial hashrate
        miner = Miner()
        mined_block = miner.mine_block(genesis_block.raw_block)
        temp_block = decode_raw_block(mined_block)
        # assert int(temp_block.nonce, 16) == self.GENESIS_NONCE
        assert int(temp_block.id, 16) <= pow(2, 256 - int(temp_block.target, 16))
        # assert temp_block.id == self.GENESIS_ID
        self.chain.append(mined_block)
