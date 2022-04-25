'''
The Block class

The Block HEADER will contain the following fields with assigned sizes:
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  version     |   32          |   8           |   4               |#
#|  prev_hash   |   256         |   64          |   32              |#
#|  merkle_root |   256         |   64          |   32              |#
#|  timestamp   |   32          |   8           |   4               |#
#|  target      |   32          |   8           |   4               |#
#|  nonce       |   32          |   8           |   4               |#
#====================================================================#

The Block TRANSACTIONS will contain the following fields with assigned sizes:
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#|  tx_num      |   VLI         |   VLI         |   VLI             |#
#|  transactions|   var         |   var         |   var             |#
#====================================================================#

The RAW block will be the hex strings of the header, followed by the tx_num VLI and the concatenation of all raw transactions.

'''

'''Imports'''
from hashlib import sha256
import datetime
from transaction import decode_raw_transaction, Transaction


class Block:
    '''

    '''
    VERSION_BITS = 32
    PREV_HASH_BITS = 256
    MERKLE_ROOT_BITS = 256
    TIMESTAMP_BITS = 32
    NONCE_BITS = 32
    TARGET_BITS = 32

    def __init__(self, version: int, prev_hash: str, target: int, nonce: int, transactions: list, timestamp=None):
        '''
        The block will calculate the merkle root from the transactions list
        Transactions will be a list of raw transaction values. The raw hex will be saved to the block.
        The hash vals of each transaction will be calculated for the merkle root.
        We can change api values to only report tx_hashes but the raw tx will be saved to the chain.
        '''
        # Get formatted version, target and nonce
        self.version = format(version, f'0{self.VERSION_BITS // 4}x')
        self.target = format(target, f'0{self.TARGET_BITS // 4}x')
        self.nonce = format(nonce, f'0{self.NONCE_BITS // 4}x')

        # Create timestamp if not used
        if timestamp is None:
            self.timestamp = format(utc_to_seconds(), f'0{self.TIMESTAMP_BITS // 4}x')
        else:
            self.timestamp = format(timestamp, f'0{self.TIMESTAMP_BITS // 4}x')

        # Create merkle root from transactions
        self.transactions = transactions
        self.merkle_root = self.calc_merkle_root()

        # Ensure merkle_root and prev_hash are 256-bits
        self.prev_hash = prev_hash
        while len(self.prev_hash) != self.PREV_HASH_BITS // 4:
            self.prev_hash = '0' + self.prev_hash
        while len(self.merkle_root) != self.MERKLE_ROOT_BITS // 4:
            self.merkle_root = '0' + self.merkle_root

        # Calculate VLI based on number of transactions
        tx_count = len(self.transactions)
        if tx_count < pow(2, 8) - 3:
            self.tx_count = format(tx_count, '02x')
        elif pow(2, 8) - 3 <= tx_count <= pow(2, 16):
            self.tx_count = 'FD' + format(tx_count, '04x')
        elif pow(2, 16) < tx_count <= pow(2, 32):
            self.tx_count = 'FE' + format(tx_count, '08x')
        else:
            self.tx_count = 'FF' + format(tx_count, '016x')

    '''
    PROPERTIES
    '''

    @property
    def raw_block(self):
        return self.raw_header + self.raw_transactions

    @property
    def raw_header(self):
        return self.version + self.prev_hash + self.merkle_root + self.timestamp + self.target + self.nonce

    @property
    def raw_transactions(self):
        transaction_string = ''
        for t in self.transactions:
            transaction_string += t
        return self.tx_count + transaction_string

    @property
    def tx_ids(self):
        return self.hashlist(self.transactions)

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
DECODING 
'''


def decode_raw_block(raw_block: str):
    '''
    The Header size will be fixed. We get the Header dict, then the transactions list and return a Block
    '''
    header_hexchars = (Block.VERSION_BITS + Block.PREV_HASH_BITS + Block.MERKLE_ROOT_BITS
                       + Block.TIMESTAMP_BITS + Block.TARGET_BITS + Block.NONCE_BITS) // 4
    header_string = raw_block[:header_hexchars]
    transaction_string = raw_block[header_hexchars:]

    header_dict = decode_raw_header(header_string)
    transactions = decode_raw_block_transactions(transaction_string)

    new_block = Block(header_dict['version'], header_dict['prev_hash'], header_dict['target'], header_dict['nonce'],
                      transactions=transactions, timestamp=header_dict['timestamp'])
    assert new_block.merkle_root == header_dict['merkle_root']
    return new_block


def decode_raw_header(raw_hdr: str):
    '''
    We read in the header and return a dict
    '''
    index1 = Block.VERSION_BITS // 4
    index2 = index1 + Block.PREV_HASH_BITS // 4
    index3 = index2 + Block.MERKLE_ROOT_BITS // 4
    index4 = index3 + Block.TIMESTAMP_BITS // 4
    index5 = index4 + Block.TARGET_BITS // 4
    index6 = index5 + Block.NONCE_BITS // 4

    version = int(raw_hdr[:index1], 16)
    prev_hash = raw_hdr[index1:index2]
    merkle_root = raw_hdr[index2:index3]
    timestamp = int(raw_hdr[index3:index4], 16)
    target = int(raw_hdr[index4:index5], 16)
    nonce = int(raw_hdr[index5:index6], 16)

    return {"version": version, "prev_hash": prev_hash, "merkle_root": merkle_root, "timestamp": timestamp,
            "target": target, "nonce": nonce}


def decode_raw_block_transactions(raw_block_tx: str) -> list:
    '''
    We will take in the raw block transactions, construct a new transaction, verify it's construction, then save the raw_transaction
    '''
    # Get number of transactions
    first_byte = int(raw_block_tx[0:2], 16)
    input_num = first_byte
    if first_byte < 253:
        tx_index = 2
    elif first_byte == 253:
        input_num = int(raw_block_tx[2:4], 16)
        tx_index = 4
    elif first_byte == 254:
        input_num = int(raw_block_tx[2:8], 16)
        tx_index = 8
    else:
        assert first_byte == 255
        input_num = int(raw_block_tx[2:16], 16)
        tx_index = 16

    # Read in transactions
    transactions = []
    temp_index = tx_index
    for x in range(0, input_num):
        new_transaction = decode_raw_transaction(raw_block_tx[temp_index:])
        transactions.append(new_transaction.raw_transaction)
        temp_index = temp_index + new_transaction.byte_size * 2

    return transactions


'''
Datetime Converter
'''


def utc_to_seconds():
    date_string = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    date_object = datetime.datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S%z')
    return int(date_object.timestamp())


def seconds_to_utc(seconds: int):
    date_object = datetime.datetime.utcfromtimestamp(seconds)
    return date_object.isoformat()
