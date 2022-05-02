'''
The Wallet class

-The wallet will generate ECC keys upon instantiation.
-The address will be related to the locking/unlocking script used in the utxos

NOTE ON RIPEMD:
    -The ripemd only seems to work through the update function
    -This means for a proper hash, we need to generate a new ripemd160 hash object each time


TODO: Allow for dynamically generated addresses from the master keys

TODO: Pull a dictionary from a web api for the seed phrase

TODO: Add prefix mapping function for address creation - the prefix will tie into the locking/unlocking script

TODO: Add the curve creation during instantiation depending on the connection to the blockchain. (Either that or
have curve coeff pouches or something.)



'''
'''
IMPORTS
'''
import pandas as pd
import secrets
import hashlib
from hashlib import sha256, sha512, sha1
from cryptography import EllipticCurve

'''
CLASS
'''


class Wallet:
    '''

    '''
    MINBIT_EXP = 7
    DICT_EXP = 11
    BASE58_LIST = ['1', '2', '3', '4', '5', '6', '7', '8', '9',
                   'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J',
                   'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T',
                   'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c',
                   'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'm',
                   'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v',
                   'w', 'x', 'y', 'z']

    def __init__(self, seed_bits=128, address_checksum_bits=32, version=0, seed=None, a=None,
                 b=None,
                 p=None):
        '''
        
        '''

        # Create the Elliptic curve
        self.curve = EllipticCurve(a, b, p)

        # Establish seed bits and checksum_bits
        self.seed_bits = max(seed_bits, pow(2, self.MINBIT_EXP))
        for x in range(1, self.DICT_EXP + 1):
            if (self.seed_bits + x) % self.DICT_EXP == 0:
                self.seed_checksum_bits = x

        assert (self.seed_bits + self.seed_checksum_bits) % self.DICT_EXP == 0

        # Create new seed or use given seen
        if seed is None:
            seed = self.get_seed()
        else:
            seed = seed

        # Use seed to generate keys and seed phrase
        self.master_keys = self.generate_master_keys(seed)
        self.address = self.get_address(version, address_checksum_bits)
        self.seed_phrase = self.get_seed_phrase(seed)  # Saving seed_phrase is only for testing.

    '''
    PROPERTIES
    '''

    @property
    def public_key(self):
        pub, _ = self.master_keys
        return pub

    @property
    def public_key_point(self):
        pub, _ = self.master_keys
        hx, hy = pub
        return (int(hx, 16), int(hy, 16))

    @property
    def compressed_public_key(self):
        x, y = self.public_key_point
        parity = y % 2
        prefix = format(2 + (1 + pow(-1, parity + 1)) // 2, '02x')
        return prefix + hex(x)[2:]

    '''
    SEED PHRASE
    '''

    def get_seed(self):
        '''
        Will generate a random seed if the wallet is instantiated without one
        '''

        seed = 0
        while seed.bit_length() != self.seed_bits:
            seed = secrets.randbits(self.seed_bits)
        return seed

    def get_seed_phrase(self, seed: int) -> list:
        '''
        Will generate a seed phrase from a given seed.
        Phrase will be index values in the dictionary.
        Dictionary size is given by 2^DICT_EXP.
        The bits and seed_checksum bits need to sum to a value divisible by DICT_EXP
        '''

        # Create binary string with bits size
        entropy = bin(seed)[2:2 + self.seed_bits]

        # Hash the entropy and take the first seed_checksum_bits
        checksum_hash = sha256(entropy.encode()).hexdigest()
        check_sum = bin(int(checksum_hash, 16))[2: 2 + self.seed_checksum_bits]

        # Concatenate the entropy and check_sum string
        index_string = entropy + check_sum

        # Verify string is divisible by DICT_EXP
        assert len(index_string) % self.DICT_EXP == 0

        # Use the string to determine word indices
        index_list = []
        for x in range(0, len(index_string) // self.DICT_EXP):
            indice = index_string[x * self.DICT_EXP: (x + 1) * self.DICT_EXP]
            index_list.append(int(indice, 2))

        # Load dictionary from file
        df_dict = pd.read_csv('./english_dictionary.txt', header=None)

        # Retrieve the words at the given index and return the seed phrase
        word_list = []
        for i in index_list:
            word_list.append(df_dict.iloc[[i]].values[0][0])
        return word_list

    def recover_seed(self, seed_phrase: list):
        '''
        Using the seed phrase, we recover the original seed.
        '''

        # Load dictionary from file
        df_dict = pd.read_csv('./english_dictionary.txt', header=None)

        # Get the dictionary index from the word
        number_list = []
        for s in seed_phrase:
            number_list.append(df_dict.index[df_dict[0] == s].values[0])

        # Express the index as a binary string of fixed DICT_EXP length
        index_string = ''
        for n in number_list:
            index_string += format(n, f"0{self.DICT_EXP}b")

        # Get the first self.bits from the binary string and return the corresponding integer
        entropy = index_string[:self.seed_bits]
        seed = int(entropy, 2)
        return seed

    '''
    ENCRYPTION KEYS
    '''

    def generate_master_keys(self, seed: int):
        '''
        We use the seed to generate a hash value of 512 bits
        We use the first 256bits to generate the keys
        We save the remaining 256bits as the Master Chain Code
        '''

        # Generate 512-bit hex string
        seed_hash512 = sha512(str(seed).encode()).hexdigest()

        # Verify bitsize = 512-bits = 64 bytes = 128 hex characters
        assert len(seed_hash512) == 128

        # Private key is the first 256 bits (64 characters)
        private_key = int(seed_hash512[:64], 16)

        # Chain code is second 256 bits
        self.chain_code = int(seed_hash512[64:], 16)

        # Generate public key from private_key
        public_key = self.curve.scalar_multiplication(private_key, self.curve.generator)

        # Verify the key is on the curvy
        assert self.curve.is_on_curve(public_key)

        # Return hex values of public and private key
        x, y = public_key
        return (hex(x), hex(y)), hex(private_key)

    '''
    ADDRESS
    '''

    def get_address(self, version: int, checksum_bits: int, prefix_bits=8):
        '''
        Using the compressed public key of the wallet, we obtain our address as follows:
            1) Hash the compressed public key using sha256
            2) Hash the result of 1) using SHA-1 - this yields a hex string with 40 characters
            3) Prepend a 1-byte (2 hex) prefix to 2) - call this the versioned hash
            4) Sha256 hash the versioned hash twice - take the first "checksum_bits" bits and append to end of versioned hash
            5) Encode the versioned hash using base58 - encode the prefix separately as it will not necessarily map to the base58 value
        '''

        # 1) Hash the compressed public key using sha256
        hash1 = sha256(self.compressed_public_key.encode()).hexdigest()

        # 2) Hash 1) using sha-1
        hash2 = sha1(hash1.encode()).hexdigest()

        # 3) Prepend a 1-byte prefix to 2)
        prefix = format(version, f'0{prefix_bits // 4}x')
        versioned_hash = prefix + hash2

        # 4) Sha256 the versioned_hash twice. Append the first "checksum_bits" bits
        hash4 = sha256(sha256(versioned_hash.encode()).hexdigest().encode()).hexdigest()
        checksum = hash4[:checksum_bits // 4]
        versioned_hash += checksum

        # 5) Encode the versioned hash using base58 - prefix will get encoded separately
        encoded_prefix = self.int_to_base58(int(prefix, 16))
        encoded_versioned_hash = self.int_to_base58(int(versioned_hash[2:], 16))

        # Verify byte sizes
        assert len(prefix) == prefix_bits // 4
        assert len(checksum) == checksum_bits // 4
        assert len(versioned_hash) - len(prefix) - len(checksum) == 40

        # Return address
        return encoded_prefix + encoded_versioned_hash

    '''
    TRANSACTIONS
    '''

    def create_transaction(self, address: str, amount: int):
        '''
        Will create a transaction
        '''
        pass

    def sign_transaction(self, tx_hash: str):
        '''
        Given a transaction hash, we return a signature (r,s) following the ECDSA.
        We use the private key of the Wallet in order to sign.
        We verify that the signature will be successfully validated using the public key

        Algorithm:
        ---------
        Let E denote the elliptic curve of the wallet and let n denote the group order.
        We emphasize that n IS NOT necessarily equal to the characteristic p of F_p.
        Let t denote the private_key.

        1) Verify that n is prime - the signature will not work if we do not have prime group order.
        2) Let Z denote the integer value of the first n BITS of the transaction hash.
        3) Select a random integer k in [1, n-1]. As n is prime, k will be invertible.
        4) Calculate the curve point (x,y) =  k * generator
        5) Compute r = x (mod n) and s = k^(-1)(Z + r * t) (mod n). If either r or s = 0, repeat from step 3.
        6) The signature is the pair (r, s)
        '''

        # 1) Verify that the curve has prime group order
        assert self.curve.has_prime_order
        n = self.curve.order

        # 2) Take the first n bits of the transaction hash
        Z = int(bin(int(tx_hash, 16))[2:2 + n], 2)

        # 3) Select a random integer k (Loop from here)
        signed = False
        sig = None
        while not signed:
            k = secrets.randbelow(n)

            # 4) Calculate curve point
            x, y = self.curve.scalar_multiplication(k, self.curve.generator)

            # 5) Compute r and s
            _, priv = self.master_keys
            private_key = int(priv, 16)
            r = x % n
            s = (pow(k, -1, n) * (Z + r * private_key)) % n

            if r != 0 and s != 0:
                h_r = hex(r)[2:]
                h_s = hex(s)[2:]

                while len(h_r) < self.curve.order.bit_length() // 4:
                    h_r = '0' + h_r
                while len(h_s) < self.curve.order.bit_length() // 4:
                    h_s = '0' + h_s

                sig = h_r + h_s
                signed = self.curve.verify_signature(sig, tx_hash, self.public_key_point)

        # 6) Return the signature (r,s) as the 128-character hex string r + s
        return sig

    '''
    BASE58
    '''

    def int_to_base58(self, num: int) -> str:
        '''
        Explanation here
        '''
        base58_string = ''
        num_copy = num
        # If num_copy is negative, keep adding 58 until it isn't
        # Negative numbers will always result in a single residue
        # Maybe think about returning error. No negative integer should ever be used.
        while num_copy < 0:
            num_copy += 58
        if num_copy == 0:
            base58_string = '1'
        else:
            while num_copy > 0:
                remainder = num_copy % 58
                base58_string = self.BASE58_LIST[remainder] + base58_string
                num_copy = num_copy // 58
        return base58_string

    def base58_to_int(self, base58_string: str) -> int:
        '''
        To convert a base58 string back to an int:
            -For each character, find the numeric index in the list
            -Multiply this numeric value by a corresponding power of 58
            -Sum all values
        '''

        sum = 0
        for x in range(0, len(base58_string)):
            numeric_val = self.BASE58_LIST.index(base58_string[x:x + 1])
            sum += numeric_val * pow(58, len(base58_string) - x - 1)
        return sum
