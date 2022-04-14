'''
The Wallet class

#TODO:
    1) Verify that all binary strings in cryptography
'''
import pandas as pd

'''Imports'''
import secrets
from hashlib import sha256

'''Wallet Class'''


class Wallet:

    def __init__(self, bits=128, checksum_bits=4, seed=None):
        '''
        We create a deterministic wallet where the seed will be expressed as dictionary words.
        We follow common practice by first generating a random_number, hashing the number and using as checksum,
            then dividing the random_number + checksum into 11-bit chunks and using these chunks as index in the dictionary
            NB: We 2048 words in the dictionary as 2^11 = 2048.

        In order to re-use a seed to instantiate a wallet of the same form, we use the first 128bits of the sha256
            hash of the seed. In this fashion, seeds close to one another generate different seed phrases
        '''

        if seed is None:
            random_number = 0
            while random_number.bit_length() != bits:
                random_number = secrets.randbits(bits)
        else:
            random_number = seed

        seed_hash = sha256(str(random_number).encode()).hexdigest()
        hash_num = int(seed_hash, 16)
        hash_binary = bin(hash_num)
        self.entropy = hash_binary[2:2 + bits]  # entropy is a string of the form '0b<...>' where '0b' is a 2byte string
        entropy_hash = sha256(self.entropy.encode()).hexdigest()
        check_sum = bin(int(entropy_hash, 16))[2: checksum_bits + 2]  # Get the first few bits from the entropy hash
        self.entropy += check_sum

        try:
            assert len(self.entropy) % 11 == 0
        except AssertionError:
            print(len(self.entropy))

        index_list = []
        for x in range(0, len(self.entropy) // 11):
            index_string = self.entropy[x * 11: (x + 1) * 11]
            index_list.append(int(index_string, 2))

        df_dict = pd.read_csv('english_dictionary.txt', header=None)

        word_list = []
        for i in index_list:
            word_list.append(df_dict.iloc[[i]].values[0][0])

        print(word_list)
