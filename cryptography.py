'''
Methods for ECC cryptography
'''

'''Imports'''
import primefac
import secrets

'''Constants'''
BITCOIN_PRIME = pow(2, 256) - pow(2, 32) - pow(2, 9) - pow(2, 8) - pow(2, 7) - pow(2, 6) - pow(2, 4) - 1
BITCOIN_GENERATOR = (0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
                     0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)

'''Mathematical Methods'''


def generate_nbit_prime(n: int):
    '''
    Will generate an n-bit prime.
    We take 4-bits as the minimum n.
    '''

    bits = max(4, n)
    num = secrets.randbits(bits)
    while not primefac.isprime(num):
        num -= 1
        if num < 2:
            num = secrets.randbits(bits)
    return num


def is_quadratic_residue(n: int, p: int) -> bool:
    '''
    returns true if n is a QR and False otherwise
    From Euler's theorem, an integer n is a QR mod p iff

    n^(p-1)/2 = 1 (mod p)
    '''
    if n % p == 0:
        return True
    return pow(n, (p - 1) // 2, p) == 1


def tonelli_shanks(n: int, p: int):
    '''
    If n is a quadratic residue mod p, then we return an integer r such that r^2 = n (mod p).
    '''
    '''Verify n is a QR'''
    if not is_quadratic_residue(n, p):
        return None

    '''Trivial case'''
    if n % p == 0:
        return 0

    '''p = 3 (mod 4) case'''
    if p % 4 == 3:
        return pow(n, (p + 1) // 4, p)

    '''General case'''
    # 1) Divide p-1 into its even and odd components by p-1 = 2^s * Q, where Q is odd and s >=1
    Q = p - 1
    s = 0
    while Q % 2 == 0:
        s += 1
        Q //= 2

    # 2) Find a quadratic non residue
    z = 2
    while is_quadratic_residue(z, p):
        z += 1

    # 3) Configure initial variables
    M = s
    c = pow(z, Q, p)
    t = pow(n, Q, p)
    R = pow(n, (Q + 1) // 2, p)

    # 4) Repeat until t == 1
    while t != 1:

        # First find the least integer i such that t^(2^i) = 1 (mod p)
        # Note that t^(2^2) = t^2
        i = 0
        factor = t
        while factor != 1:
            i += 1
            factor = (factor * factor) % p

        # Reassign variables

        exp = 2 ** (M - i - 1)
        b = pow(c, exp, p)
        M = i
        c = (b * b) % p
        t = (t * b * b) % p
        R = (R * b) % p

    return R


'''ECC Keys'''


def generate_ecc_keys(bits=256, generator=None, prime=None, a=0, b=7, private_key=None):
    '''
    We use the Secp256k1 curve y^2 = x^3 + 7
    We will generate a random generator and prime of 256 bits
    '''

    '''Get the prime'''
    if prime is None:
        p = generate_nbit_prime(bits)
    else:
        p = prime

    '''Create the curve'''
    curve = EllipticCurve(a, b, p)

    '''Get a generator'''
    if generator is None:
        g = curve.find_integer_point()  # All integer points are generators
    else:
        g = generator

    '''Verify order of generator'''
    assert curve.scalar_multiplication(p, g) is None

    '''Choose private_key or use submitted value'''
    if private_key is None:
        k = secrets.randbelow(p - 1)
    else:
        k = private_key

    '''Public key = kg'''
    public_point = curve.scalar_multiplication(k, g)
    (x, y) = public_point
    (gx, gy) = g

    public_key = [(hex(x), hex(y)), (hex(gx), hex(gy)), hex(p)]  # [(public key point), (generator point), prime)]
    private_key = hex(k)

    return public_key, private_key


'''Elliptic Curve class'''


class EllipticCurve:

    def __init__(self, a: int, b: int, p: int):
        '''
        We instantiate an elliptic curve of the form

            E = E(x,y) => y^2 = x^3  + ax + b (mod p)

        A point is a tuple or list of the form (x,y) = [x,y] - though we specify tuples.
        We let None denote the point at infinity.
        The point of infinity acts as identity for the elliptic curve group addition.
        Observe that integer points mod p will still obey symmetry about the x-axis
        That is, if (x1, y1) and (x2,y2) are such that x1 == x2 and y1 != y1
        then y1 + y2 = 0 (mod p) and (x1,y1) + (x2,y2) = point at infinity, over Z_p

        '''
        self.a = a  # Linear coefficient
        self.b = b  # Scalar coefficient
        self.p = p  # Prime characteristic

    '''
    Properties
    '''

    @property
    def discriminant(self):
        return (-16 * (4 * self.a * self.a * self.a + 27 * self.b * self.b)) % self.p

    @property
    def is_nonsingular(self):
        return self.discriminant != 0

    '''
    Methods
    '''

    def find_integer_point(self):
        '''
        Choose random x, if it's on the curve return (x,y)
        If not, increase x and try again.
        '''

        x = secrets.randbelow(self.p - 1)
        while not self.is_x_on_curve(x):
            x += 1
            if x >= self.p - 1:  # If x gets too big we choose another x
                x = secrets.randbelow(self.p - 1)

        y = self.find_y_from_x(x)
        point = (x, y)
        assert self.is_on_curve(point)
        return point

    def is_x_on_curve(self, x: int):
        '''
        If the value x^3 + ax + b (mod p) is a quadratic residue,
            then there exists some y in Z_p such that y^2 = x^3 + ax + b.
        Hence we return true if this value is a QR and false otherwise.

        We use Euler's criterion: For an odd prime p, n is a quadratic residue iff n^(p-1)/2 = 1 (mod p).
        '''

        val = (x * x * x + self.a * x + self.b) % self.p

        '''Trivial Case'''
        if val % self.p == 0:
            return True

        '''General Case'''
        return pow(val, (self.p - 1) // 2, self.p) == 1

    def find_y_from_x(self, x: int):
        '''
        Using tonelli shanks, we return y such that E(x,y) = 0, if x is on the curve.
        Note that if (x,y) is a point then (x,p-y) will be a point as well.
        '''

        '''Verify x'''
        assert self.is_x_on_curve(x)

        '''Find square root'''
        val = (x * x * x + self.a * x + self.b) % self.p
        y = tonelli_shanks(val, self.p)
        neg_y = -y % self.p
        assert self.is_on_curve((x, y))
        assert self.add_points((x, y), (x, neg_y)) is None
        return y

    def is_on_curve(self, point: tuple):
        '''
        Given a point P = (x,y) we return true if
        E(x,y) = 0 (mod p)
        '''
        '''Point at infinity case'''
        if point is None:
            return True

        '''General case'''
        x, y = point
        return (x * x * x - y * y + self.a * x + self.b) % self.p == 0

    def find_inverse(self, point: tuple):
        '''
        We return the additive inverse point inv_point such that point + inv_point = point at infinity
        '''
        if point is None:
            return None

        x, y = point
        if y == 0:
            return point
        return (x, -y % self.p)

    def add_points(self, point1: tuple, point2: tuple):
        '''
        Adding points using the elliptic curve addition rules.
        '''
        '''Check points are on curve'''
        assert self.is_on_curve(point1)
        assert self.is_on_curve(point2)

        '''Point at infinity case'''
        if point1 is None:
            return point2
        if point2 is None:
            return point1

        x1, y1 = point1
        x2, y2 = point2

        '''Addition rules'''
        if x1 == x2:
            if y1 != y2:  # Points are inverses
                return None
            elif y1 == 0:  # Point is its own inverse when lying on the x axis
                return None
            else:  # Points are the same
                m = ((3 * x1 * x1 + self.a) * pow(2 * y1, -1, self.p)) % self.p
        else:  # Points are distinct
            m = ((y2 - y1) * pow(x2 - x1, -1, self.p)) % self.p

        x3 = (m * m - x1 - x2) % self.p
        y3 = (m * (x1 - x3) - y1) % self.p

        point = (x3, y3)
        '''Verify result'''
        assert self.is_on_curve(point)
        return point

    def scalar_multiplication(self, n: int, point: tuple):
        '''
        Using the double and add algorithm, we compute nP where P = point.

        The algorithm has us break n into binary form, then for each bit,
            going from most significant to least, do the following:
            1st bit - ignore
            each bit - double previous result
            if bit = 1 - also add P

        Ex: n = 26, binary representation = 11010

        bit |   action      | result
        ----------------------------
        1   | ignore        | P
        1   | double & add  | 2P + P = 3P
        0   |   double      | 6P
        1   | double & add  | 12P +P = 13P
        0   | double        | 26P
        '''

        '''Point at infinity case'''
        if point is None or n == 0:
            return None

        '''Negative value implies multiplying the scalar by the inverse of the point'''
        if n < 0:
            n *= -1
            point = self.find_inverse(point)

        '''Proceed with algorithm'''
        bitstring = bin(n)[2:]
        bitlength = len(bitstring)
        temp_point = point
        for x in range(1, bitlength):
            temp_point = self.add_points(temp_point, temp_point)
            bit = bitstring[x:x + 1]
            if int(bit) == 1:
                temp_point = self.add_points(temp_point, point)

        '''Verify results'''
        assert self.is_on_curve(temp_point)
        return temp_point
