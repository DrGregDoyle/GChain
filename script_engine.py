'''
The Class used for running scripts to pair inputs and output utxos

We use the deque method from collections. This behaves like a stack.
We have pop which pops the first element and append which pushes to the stack.
Deque stack will be displayed from left to right with the rightmost being top of the stack

ENGINE will need to be run in the node

'''

'''Imports'''
from collections import deque
from cryptography import EllipticCurve

BITCOIN_PRIME = pow(2, 256) - pow(2, 32) - pow(2, 9) - pow(2, 8) - pow(2, 7) - pow(2, 6) - pow(2, 4) - 1
# Note that values below are int types not strings
BITCOIN_ECC_GENERATOR = (0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
                         0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)
# Both x and y are generators for Z_p^* for p = the bitcoin prime
BITCOIN_ECC_X = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798
BITCOIN_ECC_Y = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8


class ScriptEngine:
    function_map = {
        0x87: 'EQUAL',
        0xac: 'CHECKSIG_ECC'
    }

    def __init__(self, tx_hash: str, a=0, b=7):
        self.stack = deque()
        self.curve = EllipticCurve(a=a, b=b, p=BITCOIN_PRIME)
        self.tx_hash = tx_hash

    def EQUAL(self):
        data1 = self.stack.pop()
        data2 = self.stack.pop()
        return data1 == data2

    def CHECKSIG_ECC(self):
        '''
        Public key should be the public key point (x,y)
        Signature should be the (r,s) where the hashed message is the transaction hash
        '''
        public_key = self.stack.pop()
        signature = self.stack.pop()

        (x, y) = public_key
        (r, s) = signature

        s_inverse = pow(s, -1, BITCOIN_PRIME)

        u1 = (int(self.tx_hash, 16) * s_inverse) % BITCOIN_PRIME
        u2 = (r * s_inverse) % BITCOIN_PRIME

        point1 = self.curve.scalar_multiplication(u1, BITCOIN_ECC_GENERATOR)
        point2 = self.curve.scalar_multiplication(u2, public_key)
        (x1, y1) = self.curve.add_points(point1, point2)
        if point1 is None:
            return False

        return r == x1 % BITCOIN_PRIME
