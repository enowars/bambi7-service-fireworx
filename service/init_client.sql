create table if not exists 
store(
	id INTEGER primary key autoincrement,
	owner text,
	best_before integer,
	location text,
	firework_type text
);

create table if not exists 
pubkeys(
	owner text primary key,
	p integer,
	q integer,
	g integer,
	y integer
);
