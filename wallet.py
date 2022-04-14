'''
The Wallet class


'''
import pandas as pd

'''Imports'''
import secrets
from hashlib import sha256, sha512

'''Wallet Class'''


class Wallet:
    '''Formatting Variables'''
    MIN_EXP = 7
    DICT_EXP = 11

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

    def generate_master_keys(self, seed=None):
        pass
