#!/usr/bin/env python3

import sys
import os
from binascii import unhexlify, hexlify
import time

import asyncio
import aiosqlite

global DB_CONN

class Store(object):
	def __init__(self, r, w):
		self.reader = r
		self.writer = w
	
	async def write(self, s):
		if type(s) == str:
			s = s.encode()
		self.writer.write(s)
		await self.writer.drain()

	def log(self, s):
		w = open('fire.log','a')
		now = time.strftime('%Y-%m-%d %H:%M:%S') + ('%.6f' % (time.time() % 1))[1:]
		w.write('%s\t%s\n' % (now, s))
		w.close()

	async def run(self):
		while True:
			try:
				await self.write('command: ')

				line = await self.reader.readline()
				self.log(f"Received command: {line}")

				input_data = line.strip()
				if not input_data:
					break
				
				code = await self.process_command(input_data)
				await self.writer.drain()
				if code < 0:
					self.log('exit with code %d\n' % code)
					break

			except EOFError:
				break
			except (UnicodeError, IndexError) as e:
				self.log(e, file=sys.stderr)
				break

	async def process_command(self, input_data : bytes):
		data = input_data.decode().split(' ')
		command = data[0]
		await self.write(command + '\n')
		args = data[1:]

		if command == 'register':
			await self.register(args)
		elif command == 'login':
			await self.login(args)
		elif command == 'pubkey':
			await self.get_pubkey(args)
		elif command == 'exit':
			self.active_user = None
			self.writer.write(b'KTHXBYE\n')
			return -1
		return 0

		#TODO continue

	async def register(self, args):
		if len(args) != 5:
			await self.write('register needs arguments [username] [pubkey]\n')
			return
		user = args[0]
		await self.write(user + ' '.join(args[1:]) + '\n')
		p,q,g,y = [int(_) for _ in args[1:]]

		async with DB_CONN.execute('insert into pubkeys (owner,p,q,g,y) values (?,?,?,?,?);', (user,p,q,g,y)) as cursor:
			last_id = cursor.lastrowid
		
		if last_id is None:
			await self.write(b'Failed to add element to db.\n')
			self.log('Failed to add element to db.')
			return 

		await DB_CONN.commit()
		await self.write('Registration successful\n')
		self.active_user = user
		self.log('Registration successful')

	async def login(self, args):
		if len(args) != 1:
			self.writer.write(b'login needs argument [username]\n')
			self.log('login failed: wrong number of arguments')
			return
		user = args[0]
		async with DB_CONN.execute('select owner,p,q,g,y from pubkeys where owner = ?;', (user)) as cursor:
			try:
				p,q,g,y = await cursor.fetchone()[1:]
			except TypeError:
				self.writer.write(b'Key not in Database\n')
				return
		key = DSAPubKey(p,q,g,y)
		token = hexlify(os.urandom(16))
		self.writer.write(('Please sign the following token: %s\n' % token).encode())
		line = await self.reader.readline()
		try:
			r,s = [int(x) for x in line.decode().strip().split(',')]
		except ValueError as e:
			self.writer.write(b'please submit 2 decimal numbers, separated by a comma\n')
			print(e, file=sys.stderr)
		if key.verify((r,s), msg):
			self.active_user = user
		else:
			self.writer.write('Wrong signature, the incident will be reported\n')
			self.log('User %s failed signature (%d,%d)' % (user,r,s))

async def handle_connection(reader, writer):
	s = Store(reader, writer)
	await s.run()
	writer.close()
	await writer.wait_closed()

async def main():
	global DB_CONN
	DB_CONN = await aiosqlite.connect('data/store.db')

	server = await asyncio.start_server(handle_connection, host="0.0.0.0", port="1812")
	
	addr = server.sockets[0].getsockname()
	print(f'Serving on {addr}')

	async with server:
		await server.serve_forever()
		
if __name__ == "__main__":
	asyncio.run(main())
