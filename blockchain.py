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

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

'''
CLASS
'''


class Blockchain:
    '''

    '''
    COLUMNS = ['tx_id', 'tx_index', 'amount', 'locking_script']

    def __init__(self):
        '''

        '''
        self.chain = []
        self.utxos = pd.DataFrame(columns=self.COLUMNS)
        # Generate genesis block

    '''
    PROPERTIES
    '''

    @property
    def last_block(self):
        if self.chain == []:
            return []
        else:
            return self.chain[-1]

    '''
    ADD BLOCK
    '''

    def add_block(self, raw_block: str):
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
            # for i in new_transaction.inputs:
            #     # Consume output utxo's
            #     tx_id = i.tx_id
            #     tx_index = i.tx_index
            #     signature = i.signature
            #     ouput_utxo_row = self.utxos.loc[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]
            #     print(ouput_utxo_row)

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
