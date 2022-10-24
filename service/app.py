from aiohttp import web, WSCloseCode
from aiohttp_session import setup, get_session, new_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import aiosqlite
import asyncio
from base64 import urlsafe_b64decode
from crypto import DSAPubKey, gen_challenge
from cryptography import fernet
from datetime import datetime
from hashlib import md5
import json
import os
import random

base_template = """
<html>
<head>
    <title>Fireworx</title>
    <link rel="icon" type="image/x-icon" href="/static/favicon.png">
    <link rel="stylesheet" href="/static/style.css">
</head>
{body}
</html>
"""

main_template = base_template.format(body="""
<body>
    {notice}
    {navbar}
    <canvas id=canvas></canvas>
</body>
<script src="static/firework.js"></script>
<script src="static/content.js"></script>
""")

login_template = base_template.format(body="""
<body>
    {notice}
    {navbar}
    <meta id="pow_prefix" content="{pow_prefix}">
    <div id=main class=loginpage>
    <h1>Login:</h1>
    <p>Our cryptographically secure login system is based on challenge-response
    using the digital signature algorithm (DSA).<br>In other words,
    <i>military-grade</i> encryption and utterly undefeatable!! 😎</p>
    <br>
    <form id=loginform method=POST action=/login>
        <table>
        <tbody>
        <tr><th>Name:</th><td><input type=text name=name id=name></td></tr>
        <tr><th>P:</th><td><input type=text name=p id=p></td></tr>
        <tr><th>Q:</th><td><input type=text name=q id=q></td></tr>
        <tr><th>G:</th><td><input type=text name=g id=g></td></tr>
        <tr><th>Y:</th><td><input type=text name=y id=y></td></tr>
        <tr><th>Challenge:</th>
            <td><input type=text name=challenge id=challenge
                value="{challenge}" readonly></td></tr>
        <tr><th>Signature:</th>
            <td><input type=text name=signature id=signature></td></tr>
        </tbody>
        </table>
        <div>
        <a class=left onclick=gen_pubkey()>Generate</a>
        <a class=left onclick=copy_pubkey()>Copy</a>
        <a class=right onclick=do_login()>Login</a>
        </div>
    </form>
    </div>
</body>
<script src="static/spark-md5.min.js"></script>
<script src="static/content.js"></script>
""")

profile_template = base_template.format(body="""
<body>
    <div id=main class=profilepage>
        {notice}
        {navbar}
        <div class=container>
        <div id=proplist class=left>
        <h2>Properties:</h2>
        {proplist}
        </div>
        <div id=eventlog class=left>
        <h2>Events:</h2>
        {eventlog}
        </div>
        </div>
    </div>
</body>
""")

notice_template = """<meta id=notice content="{}">"""

navbar_nouser_template = """
<div id=navbar>
<div class=left><a href=/>Home</a></div>
<div class=right><a href=/login>Login</a></div>
</div>
"""

navbar_user_template = """
<div id=navbar>
<div class=left><a href=/>Home</a></div>
<div class=right><a href=/profile>{}</a></div>
<div class=right><a href=/logout>Logout</a></div>
</div>
"""

sockets = []

def html_table(entries, header=True):
    html = "<table>"
    for y, row in enumerate(entries):
        html += "<tr>"
        for x, val in enumerate(row):
            if y == 0 and header or x == 0 and not header:
                html += "<th>" + str(val) + "</th>"
            else:
                html += "<td>" + str(val) + "</td>"
        html += "</tr>"
    html += "</table>"
    return html

def html_response(html):
    return web.Response(text=html, content_type="text/html")

def gen_notice(session):
    if "error" not in session:
        return ""
    notice = notice_template.format(session["error"])
    session.pop("error")
    return notice

async def handle_main(request):
    session = await get_session(request)

    notice = gen_notice(session)
    if "user" in session:
        user = session["user"]
        navbar = navbar_user_template.format(user)
    else:
        navbar = navbar_nouser_template

    html = main_template.format(notice=notice, navbar=navbar)
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

async def handle_login(request):
    session = await get_session(request)

    if "user" in session:
        return web.HTTPFound("/")

    if request.method == "GET":
        session["challenge"] = gen_challenge()
        notice = gen_notice(session)
        navbar = navbar_nouser_template
        session["pow_prefix"] = "".join(random.choices("0123456789abcdef", k=5))
        html = login_template.format(pow_prefix=session["pow_prefix"],
                notice=notice, navbar=navbar, challenge=session["challenge"])
        return html_response(html)

    try:
        params = await request.post()
        name = params["name"]
        p = int(params["p"])
        q = int(params["q"])
        g = int(params["g"])
        y = int(params["y"])
        challenge = int(params["challenge"])
        signature = int(params["signature"])
    except KeyError as e:
        print(e)
        session["error"] = "Missing param " + str(e)
        return web.HTTPFound("/login")
    except ValueError:
        session["error"] = "Invalid / missing params"
        return web.HTTPFound("/login")

    if len(name) < 4:
        session["error"] = "Invalid username"
        return web.HTTPFound("/login")

    if "challenge" not in session or challenge != session["challenge"]:
        session["error"] = "Invalid challenge"
        return web.HTTPFound("/login")

    exists = False
    sql = "SELECT id,p,q,g,y FROM users WHERE name = ?"
    async with db.execute(sql, (name,)) as cursor:
        row = await cursor.fetchone()
        if row is not None:
            userid = row[0]
            _p, _q, _g, _y = row[1:]
            if (_p, _q, _g, _y) is not (p, q, g, y):
                session["error"] = "Wrong public key"
                return web.HTTPFound("/login")
            exists = True

    pubkey = DSAPubKey(p, q, g, y)
    #if not pubkey.verify(challenge, signature):
    #    session["error"] = "Invalid signature"
    #    return web.HTTPFound("/")

    if not exists:
        sql = "INSERT INTO users (name,p,q,g,y) values (?,?,?,?,?)"
        res = await db.execute_insert(sql, (name, p, q, g, y))
        userid = res[0]
        await db.commit()

    session["user"] = name
    session["userid"] = userid
    session["pubkey"] = {
        "p": pubkey.p,
        "q": pubkey.q,
        "g": pubkey.g,
        "y": pubkey.y
    }

    return web.HTTPFound("/")

async def handle_logout(request):
    session = await get_session(request)
    session.invalidate()
    return web.HTTPFound("/")

async def handle_profile(request):
    session = await get_session(request)

    if "userid" not in session:
        return web.HTTPFound("/")
    userid = session["userid"]

    eventlist = []
    sql = "SELECT x,y,time,wish FROM events WHERE userid = ?"
    async with db.execute(sql, (userid,)) as cursor:
        async for row in cursor:
            x = f"{row[0]:.3f}"
            y = f"{row[1]:.3f}"
            time, wish = row[2:]
            eventlist.append((time, x, y, wish))

    proplist = html_table([
        ("name", session["user"]),
        ("pub_p", session["pubkey"]["p"]),
        ("pub_q", session["pubkey"]["q"]),
        ("pub_g", session["pubkey"]["g"]),
        ("pub_y", session["pubkey"]["y"]),
    ], header=False)
    eventlog = html_table([("time", "x", "y", "wish")] + eventlist)
    notice = gen_notice(session)
    navbar = navbar_user_template.format(session["user"])
    html = profile_template.format(notice=notice, navbar=navbar,
            proplist=proplist, eventlog=eventlog)
    return html_response(html)

async def handle_gen(request):
    session = await get_session(request)

    if "pow" not in request.query:
        return web.Response(status=400, text="Missing pow")

    work = request.query["pow"].encode()
    if not md5(work).hexdigest().startswith(session["pow_prefix"]):
        return web.Response(status=400, text="Bad pow")

    # TODO generate key
    data = {
        "p": "7",
        "q": "2",
        "g": "5",
        "y": "11",
        "signature": "5",
    }
    return web.Response(status=200, text=json.dumps(data))

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
    except KeyError:
        return web.Response(status=400, text="Missing params")
    except ValueError:
        return web.Response(status=400, text="Invalid params")

    time = datetime.strftime(datetime.now(), "%H:%M:%S")
    sql = "INSERT INTO events (userid,time,wish,x,y) values (?,?,?,?,?)"
    await db.execute(sql, (userid, time, wish, x, y))
    await db.commit()

    event = {
        "type": "firework",
        "x": x,
        "y": y
    }

    print("Launching..")
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
        web.get("/login", handle_login),
        web.post("/login", handle_login),
        web.get("/logout", handle_logout),
        web.get("/profile", handle_profile),
        web.get("/gen", handle_gen),
        web.post("/launch", handle_launch),
        web.static("/static", "static")
    ])
    return web.AppRunner(app)

async def main():
    global db
    db = await aiosqlite.connect("data/db.sqlite")
    runner = create_runner()
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 1812)
    await site.start()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    loop.run_forever()

