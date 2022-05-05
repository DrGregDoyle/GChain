'''
The Miner class
'''

'''
IMPORTS
'''
from block import Block, decode_raw_block
from helpers import utc_to_seconds, seconds_to_utc
from hashlib import sha256


class Miner:
    '''

    '''
    HASHRATE_TEST = pow(10, 7)

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

        if self.is_mining:
            # Logging
            print('Successfully Mined new block')
            return test_block.raw_block
        else:
            # Logging
            print('Interrupt received by Miner')
            return ''

    def get_hashrate(self):
        '''
        '''
        start_time = utc_to_seconds()
        for x in range(0, self.HASHRATE_TEST):
            hash_string = f'Hash string number {x}'
            print(hash_string, end='\r')
            sha256(hash_string.encode())
        end_time = utc_to_seconds()
        total_seconds = end_time - start_time
        hash_rate = self.HASHRATE_TEST // total_seconds
        return hash_rate

    def stop_mining(self):
        self.is_mining = False
