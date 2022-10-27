from enochecker3 import (
    ChainDB,
    DependencyInjector,
    Enochecker,
    ExploitCheckerTaskMessage,
    GetflagCheckerTaskMessage,
    GetnoiseCheckerTaskMessage,
    HavocCheckerTaskMessage,
    InternalErrorException,
    MumbleException,
    PutflagCheckerTaskMessage,
    PutnoiseCheckerTaskMessage,
)
from enochecker3.utils import FlagSearcher, assert_in, assert_equals

from typing import Optional, Callable

from httpx import AsyncClient, Response

from bs4 import BeautifulSoup

from hashlib import md5

from logging import LoggerAdapter

from subprocess import Popen, PIPE

import crypto
import dateutil.parser
import json
import os
import random
import string
import traceback

checker = Enochecker("Fireworx", 1812)
app = lambda: checker.app

random.seed(int.from_bytes(os.urandom(16), "little"))

noise_alph = string.ascii_letters + string.digits
def noise(nmin: int, nmax: int) -> str:
    n = random.randint(nmin, nmax)
    return "".join(random.choice(noise_alph) for _ in range(n))

def divmod(a: int, b: int, n: int) -> int:
    return (a * pow(b, n - 2, n)) % n

def assert_status_code(logger: LoggerAdapter, r: Response, code: int = 200,
        parse: Optional[Callable[str, str]] = None) -> None:
    if r.status_code == code:
        return
    errlog = r.text
    if parse is not None:
        errlog = parse(errlog)
    logger.error(f"Bad status code during {r.request.method} {r.request.url.path}: " \
         + f"({r.status_code} != {code})\n{errlog}")
    raise MumbleException(f"{r.request.method} {r.request.url.path} failed")

def parse_html(logger: LoggerAdapter, r: Response) -> BeautifulSoup:
    try:
        return BeautifulSoup(r.text, "html.parser")
    except:
        logger.error(f"Invalid html from {r.request.method} {r.request.url.path}\n" \
            + r.text)
        raise MumbleException(f"Invalid html ({r.request.method} {r.request.url.path})")

def parse_notice(text: str) -> str:
    try:
        soup = BeautifulSoup(text, "html.parser")
        error = soup.select_one("meta#notice").get("content")
    except:
        raise MumbleException("Missing error from response")
    return error

async def do_register(logger: LoggerAdapter,
        client: AsyncClient, username: str) -> None:
    r = await client.get("/register")
    assert_status_code(logger, r, code=200)
    soup = parse_html(logger, r)

    privkey = crypto.DSAKey.gen()

    data = {
        "username": username,
        "p": privkey.p,
        "q": privkey.q,
        "g": privkey.g,
        "x": privkey.x,
        "y": privkey.y
    }
    r = await client.post("/register", data=data)
    assert_status_code(logger, r, code=200)

    return privkey

async def do_login(logger: LoggerAdapter, client: AsyncClient,
        username: str, privkey: crypto.DSAKey) -> None:

    r = await client.get("/challenge")
    assert_status_code(logger, r, code=200)
    try:
        challenge = int(r.text)
    except ValueError:
        raise MumbleException("Invalid challenge received")

    sig_r, sig_s = privkey.sign(challenge)

    data = {
        "username": username,
        "challenge": challenge,
        "signature": f"{sig_r},{sig_s}"
    }
    r = await client.post("/login", data=data)
    assert_status_code(logger, r, code=200)

async def do_launch(logger: LoggerAdapter,
        client: AsyncClient, wish: str) -> None:
    data = {
        "type": "firework",
        "x": str(random.uniform(0, 1)),
        "y": str(random.uniform(0, 1)),
        "wish": wish
    }
    r = await client.post("/launch", data=data)
    assert_status_code(logger, r, code=200)

async def do_profile(logger: LoggerAdapter, client: AsyncClient,
        username: Optional[str] = None) -> None:
    if username is not None:
        r = await client.get(f"/profile/{username}")
    else:
        r = await client.get("/profile")
    assert_status_code(logger, r, code=200)
    soup = parse_html(logger, r)

    data = {}
    data["profile"] = {}
    data["events"] = []

    for row in soup.select("#proplist table tr"):
        key = row.select_one("th").text
        value = row.select_one("td").text
        data["profile"][key] = value

    for i, row in enumerate(soup.select("#eventlog table tr")):
        if i == 0:
            keys = [v.text for v in row.select("th")]
        else:
            event = {}
            vals = [v.text for v in row.select("td")]
            for k,v in zip(keys, vals):
                event[k] = v
            data["events"].append(event)

    return data

@checker.putflag(0)
async def putflag(task: PutflagCheckerTaskMessage, logger: LoggerAdapter,
        client: AsyncClient, db: ChainDB) -> str:
    username = noise(10, 20)
    privkey = await do_register(logger, client, username)

    await do_launch(logger, client, task.flag)

    await db.set("info", client.cookies["AIOHTTP_SESSION"])

    return username

@checker.getflag(0)
async def getflag(task: GetflagCheckerTaskMessage,
        logger: LoggerAdapter, client: AsyncClient, db: ChainDB) -> None:
    try:
        session_cookie = await db.get("info")
    except KeyError:
        raise MumbleException("Database info missing")
    client.cookies["AIOHTTP_SESSION"] = session_cookie

    r = await client.get("/profile")
    assert_status_code(logger, r, code=200)

    assert_in(task.flag, r.text, "Flag missing")

@checker.putnoise(0)
async def putnoise(task: PutnoiseCheckerTaskMessage,
        logger: LoggerAdapter, client: AsyncClient, db: ChainDB) -> None:
    username = noise(10, 20)
    privkey = await do_register(logger, client, username)

    wish = noise(20, 50)
    await do_launch(logger, client, wish)

    keyvals = [str(v) for v in privkey.vals()]
    await db.set("info", (username, wish, keyvals))

@checker.getnoise(0)
async def getnoise(task: GetnoiseCheckerTaskMessage,
        logger: LoggerAdapter, client: AsyncClient,
        db: ChainDB, di: DependencyInjector) -> None:
    try:
        username, wish, keyvals = await db.get("info")
    except KeyError:
        raise MumbleException("Database info missing")

    keyvals = [int(v) for v in keyvals]
    privkey = crypto.DSAKey(*keyvals)
    await do_login(logger, client, username, privkey)

    data = await do_profile(logger, client)

    try:
        for k,v in privkey.pubkey().dict().items():
            assert data["profile"][k] == str(v)
    except Exception as e:
        trace = traceback.format_exc()
        logger.error(f"Invalid public key info in profile\n{trace}")
        raise MumbleException("Invalid public key info in profile")

    try:
        assert data["events"][0]["wish"] == wish
    except:
        raise MumbleException("Wish is missing from events logs")

@checker.havoc(0)
async def havoc(task: HavocCheckerTaskMessage, logger: LoggerAdapter,
        client: AsyncClient, db: ChainDB, di: DependencyInjector) -> None:
    await do_register(logger, client, noise(10, 20))

    for i in range(random.randint(1, 3)):
        await do_launch(logger, client, noise(20, 50))

@checker.exploit(0)
async def exploit_trivial_sig(task: ExploitCheckerTaskMessage,
        logger: LoggerAdapter, searcher: FlagSearcher,
        client: AsyncClient) -> Optional[str]:
    if task.attack_info == "":
        raise InternalErrorException("Missing attack info")
    username = task.attack_info

    data = await do_profile(logger, client, username)
    try:
        q = data["profile"]["q"]
    except KeyError:
        raise MumbleException("Missing pubkey q for profile")

    r = await client.get("/challenge")
    assert_status_code(logger, r, code=200)
    challenge = r.text

    data = {
        "username": username,
        "challenge": challenge,
        "signature": f"1,{q}"
    }
    r = await client.post("/login", data=data)
    assert_status_code(logger, r, code=200)

    r = await client.get("/profile")
    assert_status_code(logger, r, code=200)

    return searcher.search_flag(r.text)

@checker.exploit(1)
async def exploit_nonce_reuse(task: ExploitCheckerTaskMessage,
        logger: LoggerAdapter, searcher: FlagSearcher,
        client: AsyncClient) -> Optional[str]:
    if task.attack_info == "":
        raise InternalErrorException("Missing attack info")
    username = task.attack_info

    data = await do_profile(logger, client, username)
    try:
        p, q, g, y = [int(data["profile"][k]) for k in ("p", "q", "g", "y")]
    except KeyError as e:
        raise MumbleException(f"Missing pubkey components {e} in profile")
    except KeyError:
        raise MumbleException("Invalid pubkey components in profile")

    sigpairs = []
    for i in range(2):
        r = await client.get("/challenge")
        assert_status_code(logger, r, code=200)
        challenge = int(r.text)

        data = {
            "username": username,
            "challenge": challenge,
            "signature": f"1337,1337"
        }
        r = await client.post("/login", data=data)
        assert_status_code(logger, r, code=400)

        try:
            sig = r.text.split("\n")[-1]
            r,s = (int(v) for v in sig.split(","))
        except (KeyError, ValueError):
            raise MumbleException("Correct sig missing from login error")

        sigpairs.append((crypto.H(challenge), (r, s)))

    z1, (r1, s1) = sigpairs[0]
    z2, (r2, s2) = sigpairs[1]

    if r1 != r2:
        raise MumbleException("Signatures do not have same r, exploit fixed?")

    k = divmod(z1 - z2, s1 - s2, q)
    x = divmod(k * s1 - z1, r1, q)
    privkey = crypto.DSAKey(p, q, g, x, y)

    r = await client.get("/challenge")
    assert_status_code(logger, r, code=200)
    z3 = int(r.text)
    r3, s3 = privkey.sign(z3)
    assert privkey.pubkey().verify(z3, (r3, s3))

    await do_login(logger, client, username, privkey)

    r = await client.get("/profile")
    assert_status_code(logger, r, code=200)

    return searcher.search_flag(r.text)

if __name__ == "__main__":
    checker.run()
