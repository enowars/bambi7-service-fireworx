CREATE TABLE IF NOT EXISTS
users(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT UNIQUE,
	p TEXT,
	q TEXT,
	g TEXT,
	x TEXT,
	y TEXT
);

CREATE TABLE IF NOT EXISTS
events(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	userid INTEGER SECONDARY KEY,
	time TEXT,
	wish TEXT,
	x FLOAT,
	y FLOAT
);

CREATE INDEX users_name ON users(name);
