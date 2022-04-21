'''
The Wallet class

#TODO: Add Signature generation
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
