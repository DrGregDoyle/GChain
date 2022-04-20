'''
The Wallet class


'''
import pandas as pd

'''Imports'''
import secrets
import math
from hashlib import sha256, sha512
from cryptography import generate_ecc_keys, EllipticCurve

'''Wallet Class'''


class Wallet:
    '''Formatting Variables'''
    MIN_EXP = 7
    DICT_EXP = 11
    BITCOIN_PRIME = pow(2, 256) - pow(2, 32) - pow(2, 9) - pow(2, 8) - pow(2, 7) - pow(2, 6) - pow(2, 4) - 1
    # Note that values below are int types not strings
    BITCOIN_ECC_GENERATOR = (0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
                             0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)
    # Both x and y are generators for Z_p^* for p = the bitcoin prime
    BITCOIN_ECC_X = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798
    BITCOIN_ECC_Y = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8

    def __init__(self, bits=128, checksum_bits=4, seed=None):
        '''
        We create a deterministic wallet where the seed will be expressed as dictionary words.
        We follow common practice by first generating a random_number, hashing the number and using as checksum,
            then dividing the random_number + checksum into 11-bit chunks and using these chunks as index in the dictionary
            NB: We 2048 words in the dictionary as 2^11 = 2048.

        '''

        '''Automatically adjust bitlength and checksum if out of bounds'''
        if bits < pow(2, self.MIN_EXP):
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
            For other bitsizes, the bitlength of entropy + checksum must be divisible by 11
            (Why? 2^11 = 2048, the number of words in the dict.)
        '''

        '''Create index string = entropy + checksum'''
        entropy = bin(seed)[2:2 + self.bits]
        checksum_hash = sha256(entropy.encode()).hexdigest()
        check_sum = bin(int(checksum_hash, 16))[2: 2 + self.checksum_bits]
        index_string = entropy + check_sum

        '''Find indices'''
        index_list = []
        for x in range(0, len(index_string) // 11):
            indice = index_string[x * 11: (x + 1) * 11]
            index_list.append(int(indice, 2))

        '''Load dictionary'''
        df_dict = pd.read_csv('./english_dictionary.txt', header=None)

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

        private_key = int(private_key_string, 2)
        chain_code = int(master_chain_string, 2)  # Chain code unused for now

        pub, priv = generate_ecc_keys(bits=self.bits, generator=self.BITCOIN_ECC_GENERATOR,
                                      prime=self.BITCOIN_PRIME,
                                      private_key=private_key)
        return [pub, priv]

    def sign_transaction(self, transaction_hash: str):

        pub, priv = self.master_keys
        (h_x, h_y), (h_gx, h_gy), h_p = pub
        h_k = priv
        p = int(h_p, 16)
        generator_point = (int(h_gx, 16) % p, int(h_gy, 16) % p)
        curve = EllipticCurve(a=0, b=7, p=p)
        k = int(h_k, 16)

        signed = False
        while not signed:
            random_num = 0
            while math.gcd(random_num, p - 1) > 1:
                random_num = secrets.randbelow(p - 1)

            x1, y1 = curve.scalar_multiplication(random_num, generator_point)
            r = x1 % p
            s = pow(random_num, -1, p) * (int(transaction_hash, 16) + r * k) % p
            if r != 0 and s != 0:
                signed = True
        return (hex(r), hex(s))
