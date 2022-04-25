'''
The Miner class
'''

'''
IMPORTS
'''
from block import Block, decode_raw_block


class Miner:

    def __init__(self):
        self.is_mining = False

    def mine_block(self, raw_block: str):
        '''

        '''
        # Set mining flag
        self.is_mining = True

        # Decode the raw block
        test_block = decode_raw_block(raw_block)

        # Fix the target
        target_bits = int(test_block.target, 16)
        target = pow(2, 256 - target_bits)

        # Start Mining
        while int(test_block.id, 16) > target and self.is_mining:
            test_block.increase_nonce()

        return test_block.raw_block

    def stop_mining(self):
        self.is_mining = False