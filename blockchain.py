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
import pandas as pd
from transaction import decode_raw_transaction
from utxo import decode_raw_input_utxo, decode_raw_output_utxo, UTXO_INPUT, UTXO_OUTPUT
from cryptography import EllipticCurve

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

'''
CLASS
'''


class Blockchain:
    '''

    '''
    COLUMNS = ['tx_id', 'tx_index', 'amount', 'locking_script']

    def __init__(self, a=None, b=None, p=None):
        '''

        '''
        # Instantiate a blank chain
        self.chain = []

        # Create an empty utxo pool
        self.utxos = pd.DataFrame(columns=self.COLUMNS)

        # Create the encryption curve
        self.curve = EllipticCurve(a, b, p)

        # Generate genesis block
        # TODO: Create genesis block program

    '''
    PROPERTIES
    '''

    @property
    def last_block(self):
        if self.chain == []:
            return []
        else:
            return self.chain[-1]

    @property
    def height(self):
        return len(self.chain) - 1

    @property
    def curve_parameters(self):
        return [self.curve.a, self.curve.b, self.curve.p]

    '''
    UTXO POOL
    '''

    def consume_input(self, utxo_input: UTXO_INPUT) -> bool:
        '''
        For a given UTXO_INPUT, we find the corresponding UTXO_OUTPUT.
        We then validate the signature against the locking script.
        If valid, we remove the output utxo from the utxo_pool and return True.
        If validation fails we return False
        '''

        # Get tx_id and tx_index for output
        tx_id = utxo_input.tx_id
        tx_index = int(utxo_input.tx_index, 16)

        # Find the output signature and public key point
        output_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]

        # If the output utxo is missing, return False
        if output_index.empty:
            return False

        # Validate the signature, return False if invalid
        locking_script = self.utxos.loc[output_index]['locking_script'].values[0]
        pk_point = self.curve.get_public_key_point(locking_script)
        valid = self.curve.verify_signature(utxo_input.signature, tx_id, pk_point)
        if not valid:
            return False

        # Remove the output UTXO
        self.utxos = self.utxos.drop(self.utxos.index[output_index])
        return True

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
        if self.chain != []:
            last_block = decode_raw_block(self.last_block)
            if last_block.id != candidate_block.prev_hash:
                # Logging
                print('Previous hash error in block')
                return False

        # Input/Output trackers
        total_input_amount = 0
        total_output_amount = 0

        # Iterate over list of raw transactions
        raw_tx_list = candidate_block.transactions
        for raw in raw_tx_list:

            # Decode transaction
            new_transaction = decode_raw_transaction(raw)

            # Get input num
            input_byte = int(new_transaction.input_num[0:2], 16)
            input_num = input_byte
            if input_byte < 253:
                pass
            else:
                input_num = int(new_transaction.input_num[2:], 16)

            # Verify input num
            assert input_num == len(new_transaction.inputs)

            # Consume output utxo's
            for i in new_transaction.inputs:

                # Get tx_id and tx_index for output
                tx_id = i.tx_id
                tx_index = int(i.tx_index, 16)

                # Find the output signature and public key point
                output_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]

                # If the output utxo is missing, return False
                if output_index.empty:
                    return False

                # Validate the signature, return False if invalid
                locking_script = self.utxos.loc[output_index]['locking_script'].values[0]
                pk_point = self.curve.get_public_key_point(locking_script)
                valid = self.curve.verify_signature(i.signature, tx_id, pk_point)
                if not valid:
                    return False

                # Add the associated amount
                total_input_amount += int(self.utxos.loc[output_index]['amount'].values[0], 16)

                # Remove the output UTXO
                self.utxos = self.utxos.drop(self.utxos.index[output_index])

            # Get output num
            first_byte = int(new_transaction.output_num[0:2], 16)
            output_num = first_byte
            if first_byte < 253:
                pass
            else:
                output_num = int(new_transaction.output_num[2:], 16)

            # Add new Output UTXOs - use count for the index
            count = 0
            for t in new_transaction.outputs:
                temp_amount = t.amount
                temp_locking_script = t.locking_script
                tx_id = new_transaction.id
                tx_index = count
                new_row = pd.DataFrame([[tx_id, tx_index, temp_amount, temp_locking_script]], columns=self.COLUMNS)
                self.utxos = pd.concat([self.utxos, new_row], ignore_index=True)
                count += 1

            # Verify output utxo num
            assert output_num == count

        # Add block
        self.chain.append(candidate_block.raw_block)
        return True

    '''
    POP BLOCK
    '''

    def pop_block(self) -> bool:
        '''
        This will remove the top most block in the chain.
        We reverse the utxo's in the block.
        '''
        removed_block = decode_raw_block(self.chain.pop(-1))

        # For each transaction, we remove the output utxos from the db and restore the related inputs
        for t in removed_block.transactions:
            tx = decode_raw_transaction(t)
            id = tx.id
            output_count = 0

            # Drop all utxo outputs
            for t in tx.outputs:
                output_index = self.utxos.index[(self.utxos['tx_id'] == id) & (self.utxos['tx_index'] == output_count)]
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
                temp_amount = int(temp_output.amount, 16)
                temp_lockstring = temp_output.locking_script
                row = pd.DataFrame([[tx_id, tx_index, temp_amount, temp_lockstring]], columns=self.COLUMNS)
                self.utxos = pd.concat([self.utxos, row], ignore_index=True)

        return True

    '''
    TESTING
    '''

    def add_output_row(self, tx_id: str, tx_index: int, amount: int, locking_script: str):
        row = pd.DataFrame([[tx_id, tx_index, amount, locking_script]], columns=self.COLUMNS)
        self.utxos = pd.concat([self.utxos, row], ignore_index=True)
