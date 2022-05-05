'''
Methods for ECC cryptography

#TODO:
    -Implement Schoof's algorithm
'''

'''Imports'''
import primefac
import secrets

'''Mathematical Methods'''


def generate_nbit_prime(n: int):
    '''
    Will generate an n-bit prime.
    Defaults to 4-bits for small n.
    '''

    bits = max(4, n)
    num = secrets.randbits(bits)
    while not primefac.isprime(num) and num.bit_length() != bits:
        num -= 1
        if num < 2:
            num = secrets.randbits(bits)
    return num


def legendre_symbol(n: int, p: int) -> int:
    '''
    Returns 0 if p | n and a^(p-1)/2 % p otherwise
    '''
    if n % p == 0:
        return 0
    return pow(n, (p - 1) // 2, p)


def tonelli_shanks(n: int, p: int):
    '''
    If n is a quadratic residue mod p, then we return an integer r such that r^2 = n (mod p).
    '''
    '''Verify n is a QR'''
    if legendre_symbol(n, p) == -1:
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
    while legendre_symbol(z, p) != 1:
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


'''Elliptic Curve class'''


class EllipticCurve:
    '''
    We instantiate an elliptic curve E of the form

        y^2 = x^3 + ax + b (mod p)

    with the integers a and b and the prime p. Further, we assign the curve a generator G, which generates the
    associated abelian group comprising the rational points of E(F_p) and the point at infinity.

    Unless otherwise specified, we use the Bitcoin elliptic curve parameters:

    a = 0
    b = 7
    p = 2^256 - 2^32 - 2^9 -2^8 - 2^7 - 2^6 - 2^4 - 1


    '''
    BITCOIN_PRIME = pow(2, 256) - pow(2, 32) - pow(2, 9) - pow(2, 8) - pow(2, 7) - pow(2, 6) - pow(2, 4) - 1
    BITCOIN_GENERATOR = (0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
                         0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)
    BITCOIN_GROUPORDER = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141

    def __init__(self, a=None, b=None, p=None, generator=None, order=None):
        '''
        We instantiate an elliptic curve E of the form

            y^2 = x^3 + ax + b

        over a finite field F_p. Each curve E will have the parameters a, b and p as class variables, along with the
        order of the corresponding finite abelian group. Further, for p sufficiently small we attach a random
        generator as class variable - and for p sufficiently large we use the BITCOIN values.

        '''
        # Linear coefficient
        if a is None:
            self.a = 0
        else:
            self.a = a

        # Scalar coefficient
        if b is None:
            self.b = 7
        else:
            self.b = b

        # Field prime
        if p is None:
            self.p = self.BITCOIN_PRIME
        else:
            self.p = p

        # Generator
        if generator is None:
            self.generator = self.BITCOIN_GENERATOR
        else:
            self.generator = generator

        # Order
        if order is None:
            self.order = self.BITCOIN_GROUPORDER
        else:
            self.order = order

    '''
    Properties
    '''

    @property
    def discriminant(self):
        return (-16 * (4 * self.a * self.a * self.a + 27 * self.b * self.b)) % self.p

    @property
    def is_nonsingular(self):
        return self.discriminant != 0

    @property
    def has_prime_order(self):
        return primefac.isprime(self.order)

    '''
    Methods
    '''

    def find_generator(self):
        '''
        If the curve has prime order we return a random point. Otherwise, we find the prime divisors of the group
        order, then find a point whose scalar multiplication of the order divided by a prime divisor does not yield
        zero, for all such primes.
        '''
        if self.has_prime_order:
            return self.find_integer_point()
        else:
            unique_primes = set()
            divisor_iter = primefac.primefac(self.order)
            for d in divisor_iter:
                unique_primes.add(d)

            generator_found = False
            candidate_point = None
            while not generator_found:
                candidate_point = self.find_integer_point()
                point_list = []
                for q in unique_primes:
                    point_list.append(self.scalar_multiplication(self.order // q, candidate_point))
                if None not in point_list:
                    generator_found = True
            return candidate_point

    def find_group_order(self):
        '''
        Using the legendre symbol addition formula

        E(F_p) = \sum_{x \in F_p} ( (x^3 + ax + b) | p )

        where the right most term is the Legendre symbol
        '''

        sum = 0
        for x in range(0, self.p):
            val = x ** 3 + self.a * x + self.b
            sum += legendre_symbol(val, self.p)

        return sum + self.p + 1

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

    def find_y_from_x(self, x: int):
        '''
        Using tonelli shanks, we return y such that E(x,y) = 0, if x is on the curve.
        Note that if (x,y) is a point then (x,p-y) will be a point as well.
        '''

        # Verify x is on the curve
        assert self.is_x_on_curve(x)

        # Find the two possible y values
        val = (x ** 3 + self.a * x + self.b) % self.p
        y = tonelli_shanks(val, self.p)
        neg_y = -y % self.p

        # Check y values
        assert self.is_on_curve((x, y))
        assert self.add_points((x, y), (x, neg_y)) is None

        # Return y
        return y

    '''
    Point Verification
    '''

    def is_on_curve(self, point: tuple) -> bool:
        '''
        Return True if (x,y) is a rational point of E(F_p), that is, E(x,y) == 0 (mod p)
        '''

        # Point at infinity
        if point is None:
            return True

        # General Case
        x, y = point
        return (x ** 3 - y ** 2 + self.a * x + self.b) % self.p == 0

    def is_x_on_curve(self, x: int) -> bool:
        '''
        A residue x is on the curve E iff x^3 + ax + b is a quadratic residue modulo p.
        We use the legendre symbol on this value to return True or False as the case may be.
        '''

        # Get value
        val = x ** 3 + self.a * x + self.b

        # Trivial case
        if val % self.p == 0:
            return True

        # General case
        return legendre_symbol(val, self.p) == 1

    '''
    Group Operations
    '''

    def add_points(self, point1: tuple, point2: tuple):
        '''
        Adding points using the elliptic curve addition rules.
        '''

        # Verify points exist
        assert self.is_on_curve(point1)
        assert self.is_on_curve(point2)

        # Point at infinity cases
        if point1 is None:
            return point2
        if point2 is None:
            return point1

        # Get coordinates
        x1, y1 = point1
        x2, y2 = point2

        # Get slope if it exists
        if x1 == x2:
            if y1 != y2:  # Points are inverses
                return None
            elif y1 == 0:  # Point is its own inverse when lying on the x axis
                return None
            else:  # Points are the same
                m = ((3 * x1 * x1 + self.a) * pow(2 * y1, -1, self.p)) % self.p
        else:  # Points are distinct
            m = ((y2 - y1) * pow(x2 - x1, -1, self.p)) % self.p

        # Use the addition formulas
        x3 = (m * m - x1 - x2) % self.p
        y3 = (m * (x1 - x3) - y1) % self.p
        point = (x3, y3)

        # Verify result
        assert self.is_on_curve(point)

        # Return sum of points
        return point

    def scalar_multiplication(self, n: int, point: tuple):
        '''
        We use the double-and-add algorithm to add a point P with itself n times.

        Algorithm:
        ---------
        Break n into a binary representation (big-endian).
        Then iterate over each bit in the representation as follows:
            1) If it's the first bit, ignore;
            2) double the previous result (starting with P)
            3) if the bit = 1, add a copy of P to the result.

        Ex: n = 26. Binary representation = 11010
            bit     | action        | result
            --------------------------------
            1       | ignore        | P
            1       | double/add    | 2P + P = 3P
            0       | double        | 6P
            1       | double/add    | 12P + P = 13P
            0       | double        | 26P
        '''

        # Point at infinity case
        if point is None:
            return None

        # Scalar multiple divides group order
        if n % self.order == 0:
            return None

        # Take residue of n modulo the group order
        n = n % self.order

        # Proceed with algorithm
        bitstring = bin(n)[2:]
        temp_point = point
        for x in range(1, len(bitstring)):
            temp_point = self.add_points(temp_point, temp_point)  # Double regardless of bit
            bit = int(bitstring[x:x + 1], 2)
            if bit == 1:
                temp_point = self.add_points(temp_point, point)  # Add to the doubling if bit == 1

        # Verify results
        assert self.is_on_curve(temp_point)

        # Return point
        return temp_point

    '''
    Verify Signature
    '''

    def verify_signature(self, signature: tuple, tx_hash: str, public_key_point: tuple) -> bool:
        '''
        Given a signature pair (r,s), an encoded message tx_hash and a public key point (x,y), we verify the
        signature using the curve properties of the class.


        Algorithm
        --------
        Let n denote the group order of the elliptic curve wrt the Wallet.

        1) Verify that n is prime and that (r,s) are integers in the interval [1,n-1]
        2) Let Z be the integer value of the first n BITS of the transaction hash
        3) Let u1 = Z * s^(-1) (mod n) and u2 = r * s^(-1) (mod n)
        4) Calculate the curve point (x,y) = (u1 * generator) + (u2 * public_key)
            (where * is scalar multiplication, and + is rational point addition mod p)
        5) If r = x (mod n), the signature is valid.
        '''

        # 1) Verify our values first
        assert self.has_prime_order
        n = self.order
        r, s = signature
        assert 1 <= r <= n - 1
        assert 1 <= s <= n - 1

        # 2) Take the first n bits of the transaction hash
        Z = int(bin(int(tx_hash, 16))[2:2 + n], 2)

        # 3) Calculate u1 and u2
        s_inv = pow(s, -1, n)
        u1 = (Z * s_inv) % n
        u2 = (r * s_inv) % n

        # 4) Calculate the point
        point = self.add_points(self.scalar_multiplication(u1, self.generator),
                                self.scalar_multiplication(u2, public_key_point))

        # 5) Return True/False based on x. Account for point at infinity.
        if point is None:
            return False
        x, y = point
        return r == x % n

    '''
    Recover Point
    '''

    def get_public_key_point(self, compressed_key: str):
        '''
        We retrieve the public key point from the compressed key
        '''

        # 1 - Get the parity of y and the x integer value
        parity = int(compressed_key[:2], 16)
        x_int = int(compressed_key[2:], 16)

        # 2 - Get the y val
        y_int = self.find_y_from_x(x_int)

        # 3 - Make sure parity is correct
        if y_int % 2 != parity % 2:
            y_int = self.p - y_int

        # 4 - Verify the point
        assert self.is_on_curve((x_int, y_int))

        # 5 - Return point
        return (x_int, y_int)
