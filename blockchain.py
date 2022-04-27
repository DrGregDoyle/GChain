'''
The Blockchain class
'''

'''
IMPORTS
'''
from block import decode_raw_block, Block
import pandas as pd
from transaction import decode_raw_transaction
from utxo import decode_raw_input_utxo, decode_raw_output_utxo
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

    '''
    ADD BLOCK
    '''

    def add_block(self, raw_block: str) -> bool:
        '''

        '''
        # Decode raw block
        candidate_block = decode_raw_block(raw_block)

        # Verify target
        target_bits = int(candidate_block.target, 16)
        target = pow(2, 256 - target_bits)
        try:
            assert int(candidate_block.id, 16) <= target, 'Target error in block'
        except AssertionError as msg:
            print(msg)
            return False

        # Verify block header values
        if self.chain != []:
            last_block = decode_raw_block(self.last_block)
            try:
                assert last_block.id == candidate_block.prev_hash, 'Previous hash error in block'
            except AssertionError as msg:
                print(msg)
                return False

        # Consume UTXOs
        raw_tx_list = candidate_block.transactions
        for raw in raw_tx_list:
            new_transaction = decode_raw_transaction(raw)
            for i in new_transaction.inputs:
                # Consume output utxo's
                tx_id = i.tx_id
                tx_index = int(i.tx_index, 16)
                input_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]
                if not input_index.empty:
                    # Validate input
                    locking_script = self.utxos.loc[input_index]['locking_script'].values[0]
                    pk_point = self.curve.get_public_key_point(locking_script)
                    sig = i.signature
                    # Consume utxo if signatures match
                    if self.curve.verify_signature(sig, tx_id, pk_point):
                        self.utxos = self.utxos.drop(self.utxos.index[input_index])

            first_byte = int(new_transaction.output_num[0:2], 16)
            output_num = first_byte
            if first_byte < 253:
                pass
            else:
                output_num = int(new_transaction.output_num[2:], 16)

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
