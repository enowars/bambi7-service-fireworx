
function launch(x, y) {
	var wish = prompt("Wish upon a firework?", "");
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
function gen_pubkey() {
	if (generating) return;
	generating = true;

	prefix = document.getElementById("pow_prefix").content;
	console.log("POW prefix:", prefix)
	work = pow(prefix, 0, 10000000);
	if (work === null) {
		alert("Proof of Work failed, try again");
		generating = false;
		return;
	}

	fetch("/gen?pow=" + work)
		.then(resp => resp.text())
		.then(data => {
			if (data[0] != "{") {
				alert("Generation failed: " + data);
				console.log("Generation error: " + data);
				return;
			}
			data = JSON.parse(data);
			document.querySelector("input#p").value = data["p"]
			document.querySelector("input#q").value = data["q"]
			document.querySelector("input#g").value = data["g"]
			document.querySelector("input#y").value = data["y"]
			document.querySelector("input#signature").value = data["signature"]
		});

	generating = false;
}

function copy_pubkey() {
	text = document.querySelector("input#name").value + "\n";
	text += document.querySelector("input#p").value + "\n";
	text += document.querySelector("input#q").value + "\n";
	text += document.querySelector("input#g").value + "\n";
	text += document.querySelector("input#y").value + "\n";
	navigator.clipboard.writeText(text);
}

function do_login() {
	var loginform = document.getElementById("loginform");
	loginform.submit();
}

function event_handler() {
	let socket = new WebSocket("ws://localhost:1812/ws");

	socket.onopen = function(e) {
		// alert("Socket connected");
	}

	socket.onmessage = function(e) {
		event = JSON.parse(e.data);
		if (event.type == "firework")
			fireworks.push(new Firework(
				canvas.width / 2, canvas.height,
				canvas.width * event.x, canvas.height * event.y));
	}

	socket.onclose = function(e) {
		// alert("Socket closed");
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

	notice = document.getElementById("notice");
	if (notice !== null) {
		alert(notice.content);
	}
}
