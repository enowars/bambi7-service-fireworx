from aiohttp import web, WSCloseCode
from aiohttp_session import setup, get_session, new_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from base64 import urlsafe_b64decode
from cryptography import fernet
from datetime import datetime
from hashlib import md5

import aiosqlite
import asyncio
import crypto
import json
import os
import random
import sys
import traceback

base_template = """
<html>
<head>
    <title>Fireworx</title>
    <link rel="icon" type="image/x-icon" href="/static/favicon.png">
    <link rel="stylesheet" href="/static/style.css">
    <link rel="stylesheet" href="/static/glitch.css">
</head>
{body}
</html>
"""

main_template = base_template.format(body="""
<body class=mainpage>
<div id=main>
    {navbar}
</div>
<canvas id=canvas></canvas>
</body>
<script src="static/firework.js"></script>
<script src="static/content.js"></script>
""")

register_template = base_template.format(body="""
<body class=registerpage>
    <meta id="pow_prefix" content="{pow_prefix}">
    <div id=main>
    {navbar}
    <h1>Register:</h1>
    <p>Our cryptographically secure login system is based on challenge-response
    using the digital signature algorithm (DSA).<br>In other words,
    <i>military-grade</i> encryption and utterly undefeatable!! 😎</p>
    <br>
    <div id=registerform class=form>
    <table>
    <tbody>
    <tr><th>Name:</th><td><input type=text name=username id=username></td></tr>
    <tr><th>P:</th><td><input type=text name=p id=p></td></tr>
    <tr><th>Q:</th><td><input type=text name=q id=q></td></tr>
    <tr><th>G:</th><td><input type=text name=g id=g></td></tr>
    <tr><th>X:</th><td><input type=text name=x id=x></td></tr>
    <tr><th>Y:</th><td><input type=text name=y id=y></td></tr>
    </tbody>
    </table>
    <div>
    <a class=left onclick=gen_privkey()>Generate</a>
    <a class=left onclick=copy_privkey()>Copy</a>
    <a class=right onclick=do_register()>Register</a>
    </div>
    </div>
    <br>
    <p id=errorlog></p>
    </div>
</body>
<script src="static/spark-md5.min.js"></script>
<script src="static/content.js"></script>
""")

login_template = base_template.format(body="""
<body class=loginpage>
    <div id=main>
    {navbar}
    <h1>Login:</h1>
    <p>Our cryptographically secure login system is based on challenge-response
    using the digital signature algorithm (DSA).<br>In other words,
    <i>military-grade</i> encryption and utterly undefeatable!! 😎</p>
    <br>
    <div id=loginform class=form>
    <table>
    <tbody>
    <tr><th>Name:</th><td><input type=text name=username id=username></td></tr>
    <tr><th>Challenge:</th>
        <td><input type=text name=challenge id=challenge
            value="..." readonly></td></tr>
    <tr><th>Signature:</th>
        <td><input type=text name=signature id=signature></td></tr>
    </tbody>
    </table>
    <div>
    <a class=right onclick=do_login()>Login</a>
    </div>
    </div>
    <br>
    <p id=errorlog></p>
    </div>
</body>
<script src="static/content.js"></script>
""")

profile_template = base_template.format(body="""
<body class=profilepage>
    <div id=main>
        {navbar}
        <div class=container>
        <div id=proplist>
        <h2>Properties:</h2>
        {proplist}
        </div>
        <div id=eventlog>
        <h2>Events:</h2>
        {eventlog}
        </div>
        </div>
    </div>
</body>
""")

inspire_template = base_template.format(body="""
<body class=quotepage>
    <div id=main>
        {navbar}
        <div id=quote>
        <p>{quote}</p>
        - V
        </div>
    </div>
</body>
""")

inspire_navbar_html = """
<div class="glitch">
    <a href="/inspire">
    <span class="glitch__color glitch__color--red">Inspire</span>
    <span class="glitch__color glitch__color--blue">Inspire</span>
    <span class="glitch__color glitch__color--green">Inspire</span>
    <span class="glitch__color glitch__main">Inspire</span>
    <span class="glitch__line glitch__line--first"></span>
    <span class="glitch__line glitch__line--second"></span>
    </a>
</div>
"""

navbar_nouser_template = """
<div id=navbar>
<div class=left><a href=/>Home</a></div>
<div class=right><a href=/register>Register</a></div>
<div class=right><a href=/login>Login</a></div>
</div>
"""

navbar_user_template = """
<div id=navbar>
<div class=left><a href=/>Home</a></div>
{inspire}
<div class=right><a href=/logout>Logout</a></div>
<div class=right><a href=/profile>{username}</a></div>
</div>
"""

quotes = [
    "The service is a symbol, as is the act of exploiting it. Symbols are "
    "given power by the people. Alone, a symbol is meaningless, but with "
    "enough people, exploiting a service can change the world.",
    "Every exploit is special.",
    "Users shouldn't be afraid of services. Services should be afraid "
    "of their users.",
    "She used to tell me that god was in the code.",
    "Your pretty service took so long to build, now, with a snap of "
    "history's fingers, down it goes.",
    "Challenge authors use unsafe code to teach safe code.",
    "You wear cat ears for so long, you forget who you were underneath them."
]

sockets = []

def log(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)

def html_table(entries, header="top"):
    html = "<table>"
    for y, row in enumerate(entries):
        html += "<tr>"
        for x, val in enumerate(row):
            if y == 0 and header == "top" or x == 0 and header == "left":
                html += "<th>" + str(val) + "</th>"
            else:
                html += "<td>" + str(val) + "</td>"
        html += "</tr>"
    html += "</table>"
    return html

def html_response(html):
    return web.Response(text=html, content_type="text/html")

def gen_navbar(session):
    if "username" in session:
        if random.randint(0, 5) == 0:
            inspire = inspire_navbar_html
        else:
            inspire = ""
        return navbar_user_template.format(
            inspire=inspire, username=session["username"])
    else:
        return navbar_nouser_template

async def handle_main(request):
    session = await get_session(request)
    navbar = gen_navbar(session)
    html = main_template.format(navbar=navbar)
    return html_response(html)

async def handle_ws(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    sockets.append(ws)

    try:
        async for msg in ws:
            continue
    finally:
        sockets.remove(ws)
        await ws.close()

    return ws

async def handle_register(request):
    session = await get_session(request)

    if request.method == "GET":
        navbar = gen_navbar(session)
        session["pow_prefix"] = "".join(random.choices("0123456789abcdef", k=5))
        html = register_template.format(navbar=navbar,
                pow_prefix=session["pow_prefix"])
        return html_response(html)

    if "userid" in session:
        return web.Response(status=400, text="Already logged in")

    try:
        params = await request.post()
        username = params["username"]
        p = int(params["p"])
        q = int(params["q"])
        g = int(params["g"])
        x = int(params["x"])
        y = int(params["y"])
    except KeyError:
        return web.Response(status=400, text="Missing params")
    except ValueError:
        return web.Response(status=400, text="Invalid params")

    username = params["username"]
    if len(username) < 4:
        return web.Response(status=400, text="Username too short")

    privkey = crypto.DSAKey(p, q, g, x, y)

    try:
        sql = "INSERT INTO users (name,p,q,g,x,y) values (?,?,?,?,?,?)"
        vals = [str(v) for v in privkey.vals()]
        res = await db.execute_insert(sql, (username, *vals))
        userid = res[0]
        await db.commit()
    except Exception as e:
        traceback.print_exc()
        return web.Response(status=400, text="Registration failed (database)")

    session["username"] = username
    session["userid"] = userid

    return web.Response(status=200, text="OK")

async def handle_login(request):
    session = await get_session(request)

    if request.method == "GET":
        navbar = gen_navbar(session)
        html = login_template.format(navbar=navbar)
        return html_response(html)

    if "userid" in session:
        return web.Response(status=400, text="Already logged in")

    try:
        params = await request.post()
        username = params["username"]
        challenge = int(params["challenge"])
        r,s = params["signature"].split(",")
        signature = (int(r), int(s))
    except KeyError as e:
        return web.Response(status=400, text="Missing param " + str(e))
    except ValueError:
        if "," not in params["signature"]:
            return web.Response(status=400, text="Signature format: r,s")
        else:
            return web.Response(status=400, text="Invalid integers")

    if len(username) < 4:
        return web.Response(status=400, text="Username too short")

    if "challenge" not in session:
        return web.Response(status=400, text="Challenge not set")

    if challenge != session["challenge"]:
        return web.Response(status=400, text="Expired challenge")
    session.pop("challenge")

    sql = "SELECT id,p,q,g,x,y FROM users WHERE name = ?"
    async with db.execute(sql, (username,)) as cursor:
        row = await cursor.fetchone()
        if row is None:
            return web.Response(status=400, text="No such user")
        userid = row[0]
        privkey = crypto.DSAKey(*[int(v) for v in row[1:]])
        pubkey = privkey.pubkey()

    try:
        assert pubkey.verify(challenge, signature)
    except Exception as e:
        if not isinstance(e, AssertionError):
            trace = traceback.format_exc()
            log(f"Login signature verify failed:\n{trace}")
        text = "Verify failed! Expected signature:\n"
        try:
            r,s = privkey.sign(challenge)
            text += f"{r},{s}"
        except:
            trace = traceback.format_exc()
            log(f"Generating correct signature failed:\n{trace}")
            text += "SIGN FAILED"
        return web.Response(status=400, text=text)

    session["username"] = username
    session["userid"] = userid

    return web.Response(status=200, text="OK")

async def handle_logout(request):
    session = await get_session(request)
    session.invalidate()
    return web.HTTPFound("/")

async def handle_inspire(request):
    session = await get_session(request)
    navbar = gen_navbar(session)
    quote = random.choice(quotes)
    html = inspire_template.format(navbar=navbar, quote=quote)
    return html_response(html=html)

async def handle_profile(request):
    session = await get_session(request)
    try:
        username = request.match_info["username"]
    except:
        if "username" not in session:
            return web.HTTPFound("/login")
        username = session["username"]

    sql = "SELECT p,q,g,x,y FROM users WHERE name = ?"
    async with db.execute(sql, (username,)) as cursor:
        row = await cursor.fetchone()
        if row is None:
            return web.Response(status=400, text="Missing info (database)")
        privkey = crypto.DSAKey(*[int(v) for v in row])

    data = [("name", username),]
    if "username" in session:
        data += privkey.dict().items()
    else:
        data += privkey.pubkey().dict().items()
    proplist = html_table(data, header="left")

    data = [("time", "x", "y", "wish")]
    if "username" in session:
        userid = session["userid"]
        sql = "SELECT x,y,time,wish FROM events WHERE userid = ?"
        async with db.execute(sql, (userid,)) as cursor:
            async for row in cursor:
                x = f"{row[0]:.3f}"
                y = f"{row[1]:.3f}"
                time, wish = row[2:]
                data.append((time, x, y, wish))
    eventlog = html_table(data, header="top")

    navbar = gen_navbar(session)
    html = profile_template.format(navbar=navbar,
            proplist=proplist, eventlog=eventlog)
    return html_response(html)

async def handle_genkey(request):
    session = await get_session(request)

    if "pow_prefix" not in session:
        return web.Response(status=400, text="Invalid session")

    try:
        work = request.query["pow"]
        pow_prefix = request.query["pow_prefix"]
    except KeyError:
        return web.Response(status=400, text="Missing param " + str(e))

    if pow_prefix != session["pow_prefix"]:
        return web.Response(status=400, text="Expired pow prefix")

    md5hash = md5(work.encode()).hexdigest()
    if not md5hash.startswith(session["pow_prefix"]):
        return web.Response(status=400, text="Bad proof of work")

    try:
        privkey = crypto.DSAKey.gen()
    except Exception as e:
        return web.Response(status=400, text="Private key generation failed")

    data = {k:str(v) for k,v in privkey.dict().items()}
    return web.Response(status=200, text=json.dumps(data))

async def handle_challenge(request):
    session = await get_session(request)

    session["challenge"] = crypto.gen_challenge()
    return web.Response(text=str(session["challenge"]))

async def handle_launch(request):
    session = await get_session(request)

    if "userid" not in session:
        return web.Response(status=400, text="Not logged in")
    userid = session["userid"]

    try:
        params = await request.post()
        x = float(params["x"])
        y = float(params["y"])
        wish = params["wish"] if "wish" in params else ""
    except (KeyError, ValueError):
        return web.Response(status=400, text="Missing / invalid params")

    time = datetime.strftime(datetime.now(), "%H:%M:%S")
    sql = "INSERT INTO events (userid,time,wish,x,y) values (?,?,?,?,?)"
    await db.execute(sql, (userid, time, wish, x, y))
    await db.commit()

    event = {
        "type": "firework",
        "x": x,
        "y": y
    }

    for ws in sockets:
        await ws.send_str(json.dumps(event))

    return web.Response(status=200)

def create_runner():
    app = web.Application()
    if os.path.exists("data/.secret_key"):
        secret_key = open("data/.secret_key", "rb").read()
    else:
        fernet_key = fernet.Fernet.generate_key()
        secret_key = urlsafe_b64decode(fernet_key)
        open("data/.secret_key", "wb+").write(secret_key)
    setup(app, EncryptedCookieStorage(secret_key))
    app.add_routes([
        web.get('/', handle_main),
        web.get('/ws', handle_ws),
        web.get("/register", handle_register),
        web.post("/register", handle_register),
        web.get("/login", handle_login),
        web.post("/login", handle_login),
        web.get("/logout", handle_logout),
        web.get("/inspire", handle_inspire),
        web.get("/profile", handle_profile),
        web.get("/profile/{username}", handle_profile),
        web.get("/genkey", handle_genkey),
        web.get("/challenge", handle_challenge),
        web.post("/launch", handle_launch),
        web.static("/static", "static")
    ])
    return web.AppRunner(app)

async def main():
    global db
    db = await aiosqlite.connect("data/db.sqlite")
    runner = create_runner()
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 1812)
    await site.start()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    loop.run_forever()

