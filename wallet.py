'''
The Wallet class

-The wallet will generate ECC keys upon instantiation. The private key will be a random integer K and the public key
will be the point K*G = (x,y) on the elliptic curve of the respective blockchain, where G is the generator point.

-The address will be a BASE58 encoding of a certain hex string resulting from a sequence of hashes on the compressed
public key. A user can prove his compressed public key yields a given address by performing the same hash sequences.

-The signature will be with respect to a transaction id tx_id. It will be the compressed public key along with the
integer pair (r,s) expressed in hex, as described in the ECDSA. We include a 1 byte variable to track the length of
the hex strings.

SIGNATURE ~100 bytes
#====================================================================#
#|  field       |   bit size    |   hex chars   |   byte size       |#
#====================================================================#
#   cpk length  |   8           |   2           |   1               |#
#   cpk*        |   258         |   66          |   ~33             |#
#   r length    |   8           |   2           |   1               |#
#   r           |   256         |   64          |   32              |#
#   s length    |   8           |   2           |   1               |#
#   s           |   256         |   64          |   32              |#
#====================================================================#


'''

'''
IMPORTS
'''

from cryptography import EllipticCurve
from hashlib import sha256, sha512, sha1
from helpers import base58_to_int, int_to_base58

import pandas as pd
import secrets

'''
CLASS
'''


class Wallet:
    '''

    '''
    MINBIT_EXP = 7
    DICT_EXP = 11

    def __init__(self, seed_bits=128, address_checksum_bits=32, seed=None, a=None, b=None, p=None):
        '''
        
        '''

        # Create the Elliptic curve
        self.curve = EllipticCurve(a, b, p)

        # Establish seed bits and checksum_bits
        self.seed_bits = max(seed_bits, pow(2, self.MINBIT_EXP))
        for x in range(1, self.DICT_EXP + 1):
            if (self.seed_bits + x) % self.DICT_EXP == 0:
                self.seed_checksum_bits = x

        # TODO: Remove assert in init, replace with factory method
        assert (self.seed_bits + self.seed_checksum_bits) % self.DICT_EXP == 0

        # Create new seed or use given seen
        if seed is None:
            seed = self.get_seed()
        else:
            seed = seed

        # Use seed to generate keys and seed phrase
        self.master_keys = self.generate_master_keys(seed)
        self.address = self.get_address(address_checksum_bits)
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
        h_x = hex(x)[2:]
        return prefix + h_x

    @property
    def hex_address(self):
        return hex(base58_to_int(self.address))[2:]

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

    def get_address(self, checksum_bits: int):
        '''
        The Wallet address is a user friendly representation of an encoded compressed public key. We first encode the
        compressed public key using sha256 and subsequently encode the result using sha1. This yields a 40 character
        hex string we call the encoded public key (EPK). We then create a checksum by twice encoding the
        EPK using sha256, and taking the first checksum_bits//4 hex characters. This checksum is appended to the EPK in
        order to create the hex string we call the checksum encoded public key (CEPK). Finally,
        the CEPK is BASE58 encoded and returned as address.


        The address is largely used for display purposes. The UTXO_OUTPUT can be created using the address,
        but the raw_utxo will contain the CEPK. We note that unlike BITCOIN, we do not use prefixes as we only have
        one signature scheme.

        Using the compressed public key of the wallet, we obtain our address as follows:
            1) Take the SHA1 encoding of the SHA256 encoding of the compressed public key. This is the EPK.
            2) Take the first checksum_bits//4 hex characters of the SHA256 encoding of the SHA256 encoding of the EPK.
            This is the checksum. Then CEPK = EPK + checksum
            3) Return the BASE58 encoding of the CEPK.

        '''

        # 1) Get the EPK
        epk = sha1(sha256(self.compressed_public_key.encode()).hexdigest().encode()).hexdigest()

        # 2 ) Get the checksum and create the CEPK
        checksum = sha256(sha256(epk.encode()).hexdigest().encode()).hexdigest()[:checksum_bits // 4]
        cepk = epk + checksum

        # 3) Return the BASE58 encoding of the CEPK
        return int_to_base58(int(cepk, 16))

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
        Given a transaction hash, we return a signature (r,s) following the ECDSA, along with the compressed public key.
        We use the private key of the Wallet in order to sign.
        We verify that the signature will be successfully validated before returning the signature.

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

        Note: The pair (r,s) is the curve signature for the given tx_id. However, we include the compressed public
        key in the signature so that it's verification can be self-contained for a known EllipticCurve. Observe that
        p is a 256-bit prime, and hence this can be represented by a hexadecimal string of length 64. Thus for the
        ECDSA signature, the pair (r,s) will be each given by a hex string of length 64. Further, the signature will
        contain the compressed public key, which will be given by a hex string of length 66. Thus, the signature will be a hex string of exactly 194 characters.

        '''

        # 1) Verify that the curve has prime group order
        # TODO: Remove curve.has_prime_order - prime should be taken from the Blockchain
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
                # Get hex representation
                h_r = hex(r)[2:]
                h_s = hex(s)[2:]

                r_length = format(len(h_r), '02x')
                s_length = format(len(h_s), '02x')
                cpk_length = format(len(self.compressed_public_key), '02x')

                sig = cpk_length + self.compressed_public_key + r_length + h_r + s_length + h_s
                signed = self.curve.verify_signature((r, s), tx_hash, self.public_key_point)

        # 6) Return the signature
        return sig
