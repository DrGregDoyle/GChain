'''
The Wallet class

-The wallet will generate ECC keys upon instantiation.
-An address can be given by a base-64 (or base-58) representation of the hashed public key x-value
-(Except that both (x,y) and (x,p-y) will be valid points on the curve.


'''

'''Imports'''
import pandas as pd
import secrets
import math
from hashlib import sha256, sha512
from cryptography import EllipticCurve

'''Wallet Class'''


class Wallet:
    '''Formatting Variables'''
    MIN_EXP = 7
    DICT_EXP = 11
    BASE58_LIST = ['1', '2', '3', '4', '5', '6', '7', '8', '9',
                   'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J',
                   'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T',
                   'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c',
                   'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'm',
                   'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v',
                   'w', 'x', 'y', 'z']

    def __init__(self, bits=128, checksum_bits=4, seed=None, a=None, b=None, p=None):
        '''
        The bits and checksum_bits values are used to generate the seed.
        The curve parameters a,b and p are None by default, which means we use the BITCOIN standard values.
        '''

        '''Create the Elliptic curve'''
        self.curve = EllipticCurve(a, b, p)

        '''Automatically adjust bitlength and checksum if out of bounds'''
        if bits < pow(2, self.MIN_EXP):  # Min is 128 bits
            bits = pow(2, self.MIN_EXP)
        if (bits + checksum_bits) % self.DICT_EXP != 0:
            checksum_bits = -bits % self.DICT_EXP
        if checksum_bits == 0:
            checksum_bits = self.DICT_EXP

        self.bits = bits
        self.checksum_bits = checksum_bits

        '''Either create a new seed or recover old wallet'''
        if seed is None:
            seed = self.get_seed()
        else:
            seed = seed

        '''After instantiation we generate the master keys and the recovery phrase'''
        '''Only way to recover the seed after instantiation is from seed phrase'''
        self.master_keys = self.generate_master_keys(seed)
        self.seed_phrase = self.get_seed_phrase(seed)  # Saving seed_phrase is only for testing.
        self.address = self.get_address()

    def get_seed(self):
        '''
        Should be run once during instantiation in order to generate a seed for the Wallet.
        The seed will be needed to generate the mnemonic seed phrase for the user.
        The seed will be needed to make the "Master Keys" for the Wallet.
        The seed will be able to be recovered from the seed_phrase in order to generate the Master Keys again.
        We NEVER save the seed value to the Wallet class.
        '''

        seed = 0
        while seed.bit_length() != self.bits:
            seed = secrets.randbits(self.bits)
        return seed

    def get_seed_phrase(self, seed: int) -> list:
        '''
        Will generate a seed phrase - default is 128 bit entropy w 4 bits as checksum.
            For other bitsizes, the bitlength of entropy + checksum must be divisible by 11 = DICT_EXP
            (Why? 2^11 = 2048, the number of words in the dict. If we change the dictionary, we update DICT_EXP.)
        '''

        '''Create index string = entropy + checksum'''
        entropy = bin(seed)[2:2 + self.bits]
        checksum_hash = sha256(entropy.encode()).hexdigest()
        check_sum = bin(int(checksum_hash, 16))[2: 2 + self.checksum_bits]
        index_string = entropy + check_sum

        '''Find indices'''
        index_list = []
        for x in range(0, len(index_string) // self.DICT_EXP):
            indice = index_string[x * self.DICT_EXP: (x + 1) * self.DICT_EXP]
            index_list.append(int(indice, 2))

        '''Load dictionary'''
        df_dict = pd.read_csv('./english_dictionary.txt', header=None)  # TODO: Pull a dictionary from a web api

        '''Find indexed words and save to list'''
        word_list = []
        for i in index_list:
            word_list.append(df_dict.iloc[[i]].values[0][0])
        return word_list

    def recover_seed(self, seed_phrase: list):
        '''
        Using the seed phrase, we recover the original seed.
        '''

        '''Load dictionary'''
        df_dict = pd.read_csv('./english_dictionary.txt', header=None)

        '''Get index from word'''
        number_list = []
        for s in seed_phrase:
            number_list.append(df_dict.index[df_dict[0] == s].values[0])

        '''Change numbers into binary add concat as string'''
        index_string = ''
        for n in number_list:
            index_string += format(n, "011b")

        '''Verify'''
        entropy = index_string[:self.bits]
        seed = int(entropy, 2)
        return seed

    def generate_master_keys(self, seed: int):
        '''
        We use the seed to generate a hash value of 512 bits
        We use the first 256bits to generate the keys
        We save the remaining 256bits as the Master Chain Code
        #TODO: Add a and b as part of public_key
        '''
        seed_hash512 = sha512(str(seed).encode()).hexdigest()
        binary_string_512 = bin(int(seed_hash512, 16))[2:]
        private_key_string = binary_string_512[0:256]
        master_chain_string = binary_string_512[256:]

        pk_int = int(private_key_string, 2) % self.curve.p
        cc = int(master_chain_string, 2)  # Chain code unused for now

        (x, y) = self.curve.generate_public_key(pk_int)
        public_key = (hex(x), hex(y))
        private_key = hex(pk_int)
        return public_key, private_key

    def get_address(self):
        pub, _ = self.master_keys
        hx, hy = pub
        x = int(hx, 16)
        y = int(hy, 16)
        compressed_string = self.curve.compress_public_key((x, y))
        return self.int_to_base58(int(compressed_string, 16))

    def recover_publickey_from_address(self, address: str):
        compressed_string = '0' + hex(self.base58_to_int(address))[2:]
        (x, y) = self.curve.decompress_public_key(compressed_string)
        return (hex(x), hex(y))

    def sign_transaction(self, tx_hash: str):
        '''
        Explanation here
        '''
        if not self.curve.has_prime_order:  # Signature algorithm only works for curves w prime order group
            return -1
        else:
            n = self.curve.order

        # Get private key
        _, priv_hex = self.master_keys
        private_key = int(priv_hex, 16)

        # Find bitlength of tx_hash
        hash_binary_string = bin(int(tx_hash, 16))
        while len(hash_binary_string) > self.curve.order.bit_length():
            hash_binary_string = hash_binary_string[:-1]  # lop off bits on the right
        z = int(hash_binary_string, 2)

        # Loop until valid signature found
        signed = False
        while not signed:
            # Select cryptographically secure random integer k from [1,n-1]
            k = 0
            while math.gcd(k, n) > 1:
                k = secrets.randbelow(n)

            # Calculate k * G
            curve_point = self.curve.scalar_multiplication(k, self.curve.generator)
            x1, y1 = curve_point
            r = x1 % n
            s = (pow(k, -1, n) * (z + r * private_key)) % n

            # Repeat loop if one of r, s equals zero
            if r != 0 and s != 0:
                signed = self.verify_signature((r, s), tx_hash)
        return (hex(r), hex(s))

    def verify_signature(self, signature: tuple, tx_hash: str) -> bool:
        '''
        Verifies a given signature and tx_hash against the public key of the wallet.

        Signature will be passed in as an int tuple
        '''
        if not self.curve.has_prime_order:  # Signature algorithm only works for curves w prime order group
            return False
        else:
            n = self.curve.order

        # Get public key
        pub_hex, _ = self.master_keys
        hx, hy = pub_hex
        x = int(hx, 16)
        y = int(hy, 16)
        public_key = (x, y)

        # Get signature and s^-1
        r, s = signature
        if type(r) == str:
            r = int(r, 16)
        if type(s) == str:
            s = int(s, 16)
        s_inv = pow(s, -1, n)

        # Find bitlength of tx_hash
        hash_binary_string = bin(int(tx_hash, 16))
        while len(hash_binary_string) > self.curve.order.bit_length():
            hash_binary_string = hash_binary_string[:-1]  # lop off bits on the right
        z = int(hash_binary_string, 2)

        # Get coefficients
        u1 = (z * s_inv) % n
        u2 = (r * s_inv) % n

        point = self.curve.add_points(self.curve.scalar_multiplication(u1, self.curve.generator),
                                      self.curve.scalar_multiplication(u2, public_key))

        # Return True/False
        if point is None:
            return False

        (x1, _) = point
        return r == x1 % n

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
