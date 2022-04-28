'''
The VLI class
'''

'''
IMPORTS
'''

'''
CLASS
'''


class VLI:

    def __init__(self, integer: int):
        '''
        We create a string based on the integer value given.
        If the integer is greater than 2^64 or <0, return None.
        '''
        self.vli_string = ''
        if 0 <= integer < pow(2, 8) - 3:
            self.vli_string = format(integer, '02x')
        elif pow(2, 8) - 3 <= integer < pow(2, 16):
            self.vli_string = 'FD' + format(integer, '04x')
        elif pow(2, 16) <= integer < pow(2, 32):
            self.vli_string = 'FE' + format(integer, '08x')
        elif pow(2, 32) <= integer < pow(2, 64):
            self.vli_string = 'FF' + format(integer, '016x')
        else:
            self.vli_string = None

    @staticmethod
    def first_byte_index(first_byte: int):
        '''
        We return the number of characters a string index would increase by in order to read the VLI
        '''
        if first_byte == 253:
            return 4
        elif first_byte == 254:
            return 8
        elif first_byte == 255:
            return 16
        else:
            return 0
