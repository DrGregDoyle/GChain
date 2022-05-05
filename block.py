'''
The Block class

The Block HEADER will contain the following fields with assigned sizes:
#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  version     |   8           |   2           |   1               |#
#|  prev_hash   |   256         |   64          |   32              |#
#|  merkle_root |   256         |   64          |   32              |#
#|  target      |   32          |   8           |   4               |#
#|  nonce       |   32          |   8           |   4               |#
#|  timestamp   |   32          |   8           |   4               |#
#====================================================================#

The Block TRANSACTIONS will contain the following fields with assigned sizes:
#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  tx_num      |   32          |   8           |   4               |#
#|  transactions|   var         |   var         |   var             |#
#====================================================================#



'''

'''Imports'''
from hashlib import sha256
from helpers import utc_to_seconds
from transaction import decode_raw_transaction


class Block:
    '''

    '''
    HASH_BITS = 256
    VERSION_BITS = 8
    TARGET_BITS = 32
    NONCE_BITS = 32
    TIMESTAMP_BITS = 32
    TRANSACTION_NUM_BITS = 32

    def __init__(self, prev_hash: str, target: int, nonce: int, transactions: list, timestamp=None, version=1):
        '''
        A new Block can be instantiated using a previous hash, target value, nonce and list of raw transactions. If a
        Block needs to be recreated, it can use the same values but specify the timestamp. The Block object will save
        the transactions as a list of transaction objects. But the raw block will contain the raw transactions (
        similar to how Transactions have list of UTXO objects, but the raw tx contains the raw utxo.)

        All input values will be formatted according to hardcoded bit lengths.

        '''

        # Get formatted version, target and nonce
        self.version = format(version, f'0{self.VERSION_BITS // 4}x')
        self.target = format(target, f'0{self.TARGET_BITS // 4}x')
        self.nonce = format(nonce, f'0{self.NONCE_BITS // 4}x')

        # Create timestamp if not given
        if timestamp is None:
            self.timestamp = format(utc_to_seconds(), f'0{self.TIMESTAMP_BITS // 4}x')
        else:
            self.timestamp = format(timestamp, f'0{self.TIMESTAMP_BITS // 4}x')

        # Create list of Transaction objects
        self.transactions = []
        for raw_tx in transactions:
            new_tx = decode_raw_transaction(raw_tx)
            self.transactions.append(new_tx)

        # Create and format number of transactions
        self.tx_count = format(len(self.transactions), f'0{self.TRANSACTION_NUM_BITS // 4}x')

        # Calculate merkle root
        self.merkle_root = self.calc_merkle_root()

        # Ensure merkle_root and prev_hash are 256-bits/64 characters
        self.prev_hash = prev_hash
        while len(self.prev_hash) != self.HASH_BITS // 4:
            self.prev_hash = '0' + self.prev_hash
        while len(self.merkle_root) != self.HASH_BITS // 4:
            self.merkle_root = '0' + self.merkle_root

    '''
    PROPERTIES
    '''

    @property
    def raw_block(self):
        return self.raw_header + self.raw_transactions

    @property
    def raw_header(self):
        return self.version + self.prev_hash + self.merkle_root + self.target + self.nonce + self.timestamp

    @property
    def raw_transactions(self):
        transaction_string = ''
        for t in self.transactions:
            transaction_string += t.raw_tx
        return self.tx_count + transaction_string

    @property
    def tx_ids(self):
        id_list = []
        for t in self.transactions:
            id_list.append(t.id)
        return id_list

    @property
    def id(self):
        return sha256(self.raw_block.encode()).hexdigest()

    '''
    MERKLE ROOT
    '''

    def calc_merkle_root(self):
        '''
        Calculate Merkle Root
        1 - Compute the tx_hash of each value in the list
        2 - If list is odd, duplicate the last value
        3 - Concatenate the sequential pairs of hashes
        4 - Repeat 2 and 3 until there is only 1 hash left. This is the merkle root
        '''
        tx_hashes = self.tx_ids
        while len(tx_hashes) != 1:
            tx_hashes = self.hashpairs(tx_hashes)
        return tx_hashes[0]

    def hashlist(self, list_to_hash: list):
        hash_list = []
        for raw_hex in list_to_hash:
            hash_list.append(sha256(raw_hex.encode()).hexdigest())
        return hash_list

    def hashpairs(self, list_to_hash: list):
        if len(list_to_hash) == 1:
            return list_to_hash
        elif len(list_to_hash) % 2 == 1:
            list_to_hash.append(list_to_hash[-1])

        hash_list = []
        for x in range(0, len(list_to_hash) // 2):
            hash_list.append(sha256((list_to_hash[2 * x] + list_to_hash[2 * x + 1]).encode()).hexdigest())
        return hash_list

    '''
    MERKLE PROOF
    '''

    def find_hashpair(self, tx_id: str, hashlist: list):
        '''

        '''

        if tx_id in hashlist:
            # Return hashlist if it contains the root
            if len(hashlist) == 1:
                return tx_id
            # Balance hashlist otherwise
            elif len(hashlist) % 2 == 1:
                hashlist.append(hashlist[-1])

            index = hashlist.index(tx_id)
            if index % 2 == 0:
                # Pair is on the right
                hash_pair = hashlist[index + 1]
                return hash_pair, False
            else:
                # Pair is on the left
                hash_pair = hashlist[index - 1]
                return hash_pair, True

    def merkle_proof(self, tx_id: str):
        '''

        '''
        tx_hashes = self.tx_ids
        if tx_id in tx_hashes:
            # Find layers of tree
            layers = 0
            while pow(2, layers) < len(self.transactions):
                layers += 1

            # Construct proof
            proof = []
            temp_id = tx_id
            while len(tx_hashes) != 1:
                hash_pair, is_left = self.find_hashpair(temp_id, tx_hashes)
                proof.append({layers: hash_pair, 'is_left': is_left})
                if is_left:
                    temp_id = sha256((hash_pair + temp_id).encode()).hexdigest()
                else:
                    temp_id = sha256((temp_id + hash_pair).encode()).hexdigest()
                tx_hashes = self.hashpairs(tx_hashes)
                layers -= 1

            root = tx_hashes[0]
            proof.append({layers: root, 'root_verified': root == self.merkle_root})
            return proof
        else:
            return None

    '''
    INCREASE NONCE
    '''

    def increase_nonce(self):
        '''
        Will increase the given nonce value by 1
        '''
        self.nonce = format(int(self.nonce, 16) + 1, f'0{self.NONCE_BITS // 4}x')

    '''
    RETRIEVE TX BY ID
    '''

    def get_raw_tx(self, tx_id: str):
        try:
            index = self.tx_ids.index(tx_id)
            return self.transactions[index].raw_tx
        except TypeError:
            return ''


'''
DECODING 
'''


def decode_raw_block(raw_block: str):
    '''
    The Header size will be fixed. We get the Header dict, then the transactions list and return a Block
    '''

    # Get number of hex chars
    header_hexchars = (Block.VERSION_BITS + Block.HASH_BITS + Block.HASH_BITS
                       + Block.TIMESTAMP_BITS + Block.TARGET_BITS + Block.NONCE_BITS) // 4

    # Break up string into header and transaction
    header_string = raw_block[:header_hexchars]
    transaction_string = raw_block[header_hexchars:]

    # Decode the raw header and raw transaction
    header_dict = decode_raw_header(header_string)
    transactions = decode_raw_block_transactions(transaction_string)

    # Create the block
    new_block = Block(header_dict['prev_hash'], header_dict['target'], header_dict['nonce'],
                      transactions=transactions, timestamp=header_dict['timestamp'], version=header_dict['version'])

    # Verify block construction
    assert new_block.merkle_root == header_dict['merkle_root']

    # Return block
    return new_block


def decode_raw_header(raw_hdr: str):
    '''
    We read in the header and return a dict
    '''
    # Determine block indices
    index1 = Block.VERSION_BITS // 4
    index2 = index1 + Block.HASH_BITS // 4
    index3 = index2 + Block.HASH_BITS // 4
    index4 = index3 + Block.TARGET_BITS // 4
    index5 = index4 + Block.NONCE_BITS // 4
    index6 = index5 + Block.TIMESTAMP_BITS // 4

    # Get variables from string in proper type
    version = int(raw_hdr[:index1], 16)
    prev_hash = raw_hdr[index1:index2]
    merkle_root = raw_hdr[index2:index3]
    target = int(raw_hdr[index3:index4], 16)
    nonce = int(raw_hdr[index4:index5], 16)
    timestamp = int(raw_hdr[index5:index6], 16)

    # Return dictionary with corresponding values
    return {"version": version, "prev_hash": prev_hash, "merkle_root": merkle_root,
            "target": target, "nonce": nonce, "timestamp": timestamp}


def decode_raw_block_transactions(raw_block_tx: str) -> list:
    '''
    We will take in the raw block transactions, construct a new transaction, verify its construction, then save the
    raw_transactions. We emphasize that we return a list of raw transactions, as the list will be used to instantiate
    a Block
    '''
    # Get number of transactions
    tx_num = int(raw_block_tx[:Block.TRANSACTION_NUM_BITS // 4])

    # Read in transactions
    transactions = []
    temp_index = Block.TRANSACTION_NUM_BITS // 4
    for x in range(0, tx_num):
        new_raw_tx = decode_raw_transaction(raw_block_tx[temp_index:]).raw_tx
        transactions.append(new_raw_tx)
        temp_index = temp_index + len(new_raw_tx)

    return transactions
