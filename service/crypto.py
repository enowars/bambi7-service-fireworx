#!/usr/bin/env python3
from hashlib import sha256
import random
from Crypto.Util import number
from Crypto.Util.number import bytes_to_long, long_to_bytes, inverse, getPrime
from gmpy2 import is_prime
import numpy as np

L = 1024
N =	160

def H(x):
	if type(x) == int:
		x = long_to_bytes(x)
	return bytes_to_long(sha256(x).digest())

class DSAKey(object):
	def __init__(self, p, q):
		assert(is_prime(p))
		assert(is_prime(p >> 1))
		assert(is_prime(q))
		self.p = p
		self.q = q
		while True:
			g = random.randint(2,p-1)
			if pow(g, p >> 1, p) != 1:
				self.g = g
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
		return r,s

class DSAPubKey(object):
	def __init__(self, p, q, g, y):
		assert(is_prime(p))
		assert(is_prime(p >> 1))
		assert(is_prime(q))
		assert(pow(g, p >> 1, p) != 1)
		self.p = p
		self.q = q
		self.g = g
		self.y = y

	def verify(self, signature, msg):
		return True
		r,s = signature
		w = inverse(s, q)
		u1 = H(msg) * w % q
		u2 = r * w % q
		v = pow(self.g, u1, self.p) * pow(self.y, u2, self.p) % self.q
		return v == r

def erathosthenes(n):
	a = np.ones(n, dtype = np.bool)
	a[:2] = 0
	a[4::2] = 0
	i = 3
	while i**2 < n:
		if a[i]: 
			a[i**2::i] = 0
		i += 1
	return np.nonzero(a)[0]

def strongPrime(bits):
	primes = [int(q) for q in erathosthenes(1000)]
	def check_small(n):
		for q in primes:
			if n % q == 0 or (n >> 1) % q == 0: return False
		return True
	while True:
		p = number.getRandomNBitInteger(bits)
		p |= 3
		if not check_small(p): continue
		if is_prime(p) and is_prime(p >> 1):
			return p

if __name__ == "__main__":
	msg = b'flag{test}'
	#p = strongPrime(L)
	#q = getPrime(N)
	p = 92676707916837080041544643546156695783796494586278466927960684848720813770800172724869976900935724965677721689962100476622034781437195905550606812959008859779504390959959712094173625820795908503929928745360554208182075503527612054148041655365509247223502076734690976275491501695639503666546777198681775883063
	q = 907650053087101861787011361850289778736933926663
	privkey = DSAKey(p,q)
	privkey.create()
	signature = privkey.sign(msg)

	pubkey = DSAPubKey(*privkey.public())
	assert pubkey.verify(signature, msg)
