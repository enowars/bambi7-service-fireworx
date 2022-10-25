#!/usr/bin/env python3

import random
from hashlib import sha256

from Crypto.Util import number
from Crypto.Util.number import bytes_to_long, getPrime, inverse, long_to_bytes
from gmpy2 import is_prime

L = 1024
N = 160

def H(x):
    if type(x) == int:
        x = long_to_bytes(x)
    return bytes_to_long(sha256(x).digest())


class DSAKey:
    def __init__(self, L, N):
        q = getPrime(N)
        low = (1 << (L-1)) // q + 1
        up = (1 << L) // q
        while True:
            factor = number.getRandomRange(low, up + 1)
            p = factor * q + 1
            if is_prime(p): break
        self.p = p
        self.q = q
        while True:
            self.g = pow(number.getRandomRange(2, p), factor, p)
            if  self.g != 1:
                break

    def create(self):
        self.x = random.randint(1, self.q - 1)
        self.y = pow(self.g, self.x, self.p)

    def public(self):
        return self.p, self.q, self.g, self.y

    def sign(self, msg):
        k = H(self.y)
        r = pow(self.g, k, self.p) % self.q
        s = inverse(k, self.q) * (H(msg) + r * self.x) % self.q
        return r, s


class DSAPubKey:
    def __init__(self, p, q, g, y):
        assert is_prime(p)
        assert is_prime(q)
        assert pow(g, q, p) == 1
        assert g != 1
        self.p = p
        self.q = q
        self.g = g
        self.y = y

    def verify(self, msg, signature):
        r, s = signature
        w = inverse(s, self.q)
        u1 = H(msg) * w % self.q
        u2 = r * w % self.q
        v = (pow(self.g, u1, self.p) * pow(self.y, u2, self.p) % self.p) % self.q
        return v == r

def gen_challenge():
    return bytes_to_long(random.randbytes(16))

if __name__ == "__main__":
    msg = b"flag{test}"

    privkey = DSAKey(L,N)
    privkey.create()
    signature = privkey.sign(msg)

    pubkey = DSAPubKey(*privkey.public())
    assert pubkey.verify(msg, signature)
