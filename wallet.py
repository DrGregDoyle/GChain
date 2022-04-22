'''
The Wallet class

-The wallet will generate ECC keys upon instantiation.
-The address will be related to the locking/unlocking script used in the utxos

###NOTE ON RIPEMD
    -The ripemd only seems to work through the update function
    -This means for a proper hash, we need to generate a new ripemd160 hash object each time


#TODO: Allow for dynamically generated addresses from the master keys


'''

'''Imports'''
import pandas as pd
import secrets
import math
import hashlib
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

    def __init__(self, bits=128, seed_checksum_bits=4, address_checksum_bits=32, version=0, seed=None, a=None, b=None,
                 p=None):
        '''
        The bits and checksum_bits values are used to generate the seed.
        The curve parameters a,b and p are None by default, which means we use the BITCOIN standard values.
        '''

        '''Create the Elliptic curve'''
        self.curve = EllipticCurve(a, b, p)

        '''Automatically adjust bitlength and checksum if out of bounds'''
        if bits < pow(2, self.MIN_EXP):  # Min is 128 bits
            bits = pow(2, self.MIN_EXP)
        if (bits + seed_checksum_bits) % self.DICT_EXP != 0:
            seed_checksum_bits = -bits % self.DICT_EXP
        if seed_checksum_bits == 0:
            seed_checksum_bits = self.DICT_EXP

        self.bits = bits
        self.seed_checksum_bits = seed_checksum_bits

        '''Either create a new seed or recover old wallet'''
        if seed is None:
            seed = self.get_seed()
        else:
            seed = seed

        '''After instantiation we generate the master keys and the recovery phrase'''
        '''Only way to recover the seed after instantiation is from seed phrase'''
        self.master_keys = self.generate_master_keys(seed)
        self.seed_phrase = self.get_seed_phrase(seed)  # Saving seed_phrase is only for testing.
        self.address = self.get_address(version, address_checksum_bits)

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
        check_sum = bin(int(checksum_hash, 16))[2: 2 + self.seed_checksum_bits]
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
        '''
        seed_hash512 = sha512(str(seed).encode()).hexdigest()
        binary_string_512 = bin(int(seed_hash512, 16))[2:]
        private_key_string = binary_string_512[0:256]
        master_chain_string = binary_string_512[256:]

        pk_int = int(private_key_string, 2) % self.curve.p
        cc = int(master_chain_string, 2)  # Chain code unused for now

        (x, y) = self.curve.generate_public_key(pk_int)
        return (hex(x), hex(y)), hex(pk_int)

    def get_address(self, version: int, checksum_bits: int, prefix_bits=8):
        '''
        Address method here:
        '''
        # Get public key as int
        (hx, hy), _ = self.master_keys
        x = int(hx, 16)
        y = int(hy, 16)

        # Compress public key to hex string
        c_pubkey = self.curve.compress_public_key((x, y))

        ##Hash twice##
        # Sha256 first
        pub_hash1 = sha256(c_pubkey.encode()).hexdigest()

        # Ripemd160
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(pub_hash1.encode())
        hashed_cpubkey = ripemd160.hexdigest()

        # Prefix
        prefix = format(version, f'0{prefix_bits // 4}x')  # Make the version have full byte count

        # Checksum
        versioned_cpubkey = prefix + hashed_cpubkey
        hash1 = sha256(versioned_cpubkey.encode()).hexdigest()
        hash2 = sha256(hash1.encode()).hexdigest()
        checksum = hash2[0:checksum_bits // 4]

        payload = versioned_cpubkey + checksum
        final_prefix = payload[0:prefix_bits // 4]
        final_payload = payload[prefix_bits // 4:]

        # Verify address size by # of hex chars. 50 chars = 25 bytes
        assert len(payload) == 40 + prefix_bits // 4 + checksum_bits // 4
        assert len(final_prefix) == prefix_bits // 4
        assert len(final_payload) == 40 + checksum_bits // 4

        # We use int_to_base58 for the prefix - need a mapping function
        return self.int_to_base58(int(final_prefix, 16)) + self.int_to_base58(int(final_payload, 16))

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
