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
from helpers import get_signature_parts
from transaction import decode_raw_transaction
from utxo import decode_raw_input_utxo, decode_raw_output_utxo, UTXO_INPUT, UTXO_OUTPUT
from cryptography import EllipticCurve
from wallet import Wallet
from vli import VLI
from hashlib import sha256, sha1

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
    ADDRESS_DIGEST_BITS = 160

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
        return Wallet().int_to_base58(int(raw_addy + checksum, 16)) == address

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

                # Find the associated output utxo
                output_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]

                # If the output utxo is missing, return False
                if output_index.empty:
                    # Logging
                    print('Output index empty error')
                    return False

                # Validate the input signature against the output address
                output_address = self.utxos.loc[output_index]['address'].values[0]
                valid = self.validate_signature(i.signature, tx_id, output_address)
                if not valid:
                    # Logging
                    print('Valid signature error')
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
                new_row = pd.DataFrame([[new_transaction.id, count, t.amount, t.address]], columns=self.COLUMNS)
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
                temp_address = temp_output.address
                row = pd.DataFrame([[tx_id, tx_index, temp_amount, temp_address]], columns=self.COLUMNS)
                self.utxos = pd.concat([self.utxos, row], ignore_index=True)

        return True

    '''
    TESTING
    '''

    def add_output_row(self, tx_id: str, tx_index: int, amount: int, address: str):
        row = pd.DataFrame([[tx_id, tx_index, amount, address]], columns=self.COLUMNS)
        self.utxos = pd.concat([self.utxos, row], ignore_index=True)
