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
    def __init__(self, p, q, g, x, y):
        self.p = p
        self.q = q
        self.g = g
        self.x = x
        self.y = y

    def vals(self):
        return (self.p, self.q, self.g, self.x, self.y)

    def dict(self):
        return {
            "p": self.p,
            "q": self.q,
            "g": self.g,
            "x": self.x,
            "y": self.y
        }

    def gen(L=L, N=N):
        q = getPrime(N)
        low = (1 << (L-1)) // q + 1
        up = (1 << L) // q
        while True:
            factor = number.getRandomRange(low, up + 1)
            p = factor * q + 1
            if is_prime(p): break
        while True:
            g = pow(number.getRandomRange(2, p), factor, p)
            if g != 1:
                break
        x = random.randint(1, q - 1)
        y = pow(g, x, p)
        return DSAKey(p, q, g, x, y)

    def pubkey(self):
        return DSAPubKey(self.p, self.q, self.g, self.y)

    def sign(self, msg):
        k = H(self.y)
        r = pow(self.g, k, self.p) % self.q
        s = inverse(k, self.q) * (H(msg) + r * self.x) % self.q
        return r, s


class DSAPubKey:
    def __init__(self, p, q, g, y):
        self.p = p
        self.q = q
        self.g = g
        self.y = y

    def vals(self):
        return (self.p, self.q, self.g, self.y)

    def dict(self):
        return {
            "p": self.p,
            "q": self.q,
            "g": self.g,
            "y": self.y
        }

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

    privkey = DSAKey.gen()
    signature = privkey.sign(msg)

    pubkey = privkey.pubkey()
    assert pubkey.verify(msg, signature)
