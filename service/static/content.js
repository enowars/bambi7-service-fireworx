
function launch(x, y) {
	var wish = prompt("Wish upon a firework?", "");
	if (wish === null) {
		wish = "";
	}
	var xhr = new XMLHttpRequest();
	var params = new URLSearchParams({x: x, y: y, wish: wish})
	xhr.open("POST", "/launch", true);
	xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
	xhr.onload = () => {
		if (xhr.status != 200) {
			alert("Launch failed: " + xhr.responseText);
		}
	}
	xhr.send(params.toString());
}

function pow(beginsWith, min, max) {
	var time = new Date().getTime();
	for (var i = min; i < max; i++) {
		var hash = SparkMD5.hash(new String(i));
		if (hash.indexOf(beginsWith) === 0) {
			console.log(hash);
			return new String(i);
		}
	}
	return null;
}

var generating = false;
function gen_privkey() {
	if (generating) return;
	generating = true;

	var log = document.querySelector("p#errorlog")
	log.innerHTML = ""

	prefix = document.getElementById("pow_prefix").content;
	console.log("POW prefix:", prefix)
	work = pow(prefix, 0, 10000000);
	if (work === null) {
		log.innerHTML = "Proof of Work failed, try again";
		generating = false;
		return;
	}

	fetch("/genkey?pow_prefix=" + prefix + "&pow=" + work)
		.then(resp => resp.text())
		.then(data => {
			if (data[0] != "{") {
				log.innerHTML = "Generation failed:\n" + data;
				return;
			}
			data = JSON.parse(data);
			document.querySelector("input#p").value = data["p"]
			document.querySelector("input#q").value = data["q"]
			document.querySelector("input#g").value = data["g"]
			document.querySelector("input#x").value = data["x"]
			document.querySelector("input#y").value = data["y"]
		});

	generating = false;
}

function copy_privkey() {
	text = document.querySelector("input#name").value + "\n";
	text += document.querySelector("input#p").value + "\n";
	text += document.querySelector("input#q").value + "\n";
	text += document.querySelector("input#g").value + "\n";
	text += document.querySelector("input#x").value + "\n";
	text += document.querySelector("input#y").value + "\n";
	navigator.clipboard.writeText(text);
}

function set_challenge() {
	fetch("/challenge").then(r => r.text()).then(text => {
		document.querySelector("input#challenge").value = text;
	})
}

function do_login() {
	username = document.querySelector("input#username").value;
	challenge = document.querySelector("input#challenge").value;
	signature = document.querySelector("input#signature").value;
	var params = new URLSearchParams({
		username: username,
		challenge: challenge,
		signature: signature
	})

	var log = document.querySelector("p#errorlog")
	log.innerHTML = ""

	var xhr = new XMLHttpRequest();
	xhr.open("POST", "/login", true);
	xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
	xhr.onload = () => {
		if (xhr.status == 200) {
			window.location.replace("/");
		} else {
			log.innerHTML = xhr.responseText;
			set_challenge()
		}
	}
	xhr.send(params.toString());
}

function do_register() {
	username = document.querySelector("input#username").value;
	p = document.querySelector("input#p").value;
	q = document.querySelector("input#q").value;
	g = document.querySelector("input#g").value;
	x = document.querySelector("input#x").value;
	y = document.querySelector("input#y").value;
	var params = new URLSearchParams({
		username: username,
		p: p,
		q: q,
		g: g,
		x: x,
		y: y
	})

	var log = document.querySelector("p#errorlog")
	log.innerHTML = ""

	var xhr = new XMLHttpRequest();
	xhr.open("POST", "/register", true);
	xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
	xhr.onload = () => {
		if (xhr.status == 200) {
			window.location.replace("/");
		} else {
			log.innerHTML = xhr.responseText;
		}
	}
	xhr.send(params.toString());
}

function event_handler() {
	let socket = new WebSocket("ws://localhost:1812/ws");

	socket.onmessage = function(e) {
		event = JSON.parse(e.data);
		if (event.type == "firework")
			fireworks.push(new Firework(
				canvas.width / 2, canvas.height,
				canvas.width * event.x, canvas.height * event.y));
	}
}

window.onload = function() {
	var canvas = document.getElementById("canvas");
	if (canvas !== null) {
		canvas.addEventListener("mousedown", function(e) {
			mx = e.pageX - canvas.offsetLeft;
			my = e.pageY - canvas.offsetTop;
			launch(mx / canvas.clientWidth, my / canvas.clientHeight);
		});

		firework_loop()

		event_handler()
	}

	loginform = document.getElementById("loginform")
	if (loginform !== null) {
		set_challenge();
	}
}
