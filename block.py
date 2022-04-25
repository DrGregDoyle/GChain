'''
The Block class

Size    | Field
---------------------------------
4 bytes | Version
32 bytes| Previous block hash
32 bytes| Merkle Root
4 bytes | Timestamp
4 bytes | Target
4 bytes | Nonce
'''

'''Imports'''
from hashlib import sha256


class Block:

    def __init__(self, version: int, prev_hash: str, target: int, nonce: int, transactions: list):
        '''
        The block will calculate the merkle root from the transactions list
        Transactions will be a list of raw transaction values. The raw hex will be saved to the block.
        The hash vals of each transaction will be calculated for the merkle root.
        We can change api values to only report tx_hashes but the raw tx will be saved to the chain.
        '''
        self.version = version
        self.prev_hash = prev_hash
        self.target = target
        self.nonce = nonce
        self.transactions = transactions
        self.merkle_root = self.calc_merkle_root()

    '''
    PROPERTIES
    '''

    @property
    def tx_ids(self):
        return self.hashlist(self.transactions)

    @property
    def tx_count(self):
        return len(self.transactions)

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
            while pow(2, layers) < self.tx_count:
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
