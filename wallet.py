'''
The Wallet class


'''
import pandas as pd

'''Imports'''
import secrets
from hashlib import sha256

'''Wallet Class'''


class Wallet:

    def __init__(self, bits=128, checksum_bits=4):
        '''
        We create a deterministic wallet where the seed will be expressed as dictionary words.
        We follow common practice by first generating a random_number, hashing the number and using as checksum,
            then dividing the random_number + checksum into 11-bit chunks and using these chunks as index in the dictionary
            NB: We 2048 words in the dictionary as 2^11 = 2048.

        '''
        self.bits = bits
        self.checksum_bits = checksum_bits

        '''Verify entropy + checksum_bits'''
        try:
            assert (self.bits + self.checksum_bits) % 11 == 0
        except AssertionError:
            return None

    def get_seed_phrase(self, seed=None) -> list:
        '''
        Will generate a seed phrase - default is 128 bit entropy w 4 bits as checksum.
            For other bitsizes, the bitlength of entropy + checksum must be divisible by 11
        '''

        '''Generate new seed or use submitted'''
        if seed is None:
            seed = 0
            while seed.bit_length() < self.bits:
                seed = secrets.randbits(self.bits)
        else:
            seed = seed

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
