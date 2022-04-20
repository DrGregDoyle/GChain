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


class Block:

    def __init__(self):
        pass