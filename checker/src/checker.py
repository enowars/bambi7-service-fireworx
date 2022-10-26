from enochecker3 import (
    ChainDB,
    DependencyInjector,
    Enochecker,
    ExploitCheckerTaskMessage,
    GetflagCheckerTaskMessage,
    GetnoiseCheckerTaskMessage,
    InternalErrorException,
    MumbleException,
    PutflagCheckerTaskMessage,
    PutnoiseCheckerTaskMessage,
)
from enochecker3.utils import FlagSearcher, assert_in, assert_equals

from typing import Optional

from httpx import AsyncClient

from bs4 import BeautifulSoup

from hashlib import md5

from logging import LoggerAdapter

from subprocess import Popen, PIPE

import crypto
import dateutil.parser
import string
import random
import os

checker = Enochecker("Fireworx", 1812)
app = lambda: checker.app

random.seed(int.from_bytes(os.urandom(16), "little"))

noise_alph = string.ascii_letters + string.digits
def noise(nmin: int, nmax: int) -> str:
    n = random.randint(nmin, nmax)
    return "".join(random.choice(noise_alph) for _ in range(n))

def str2epoch(text: str) -> int:
    date = dateutil.parser.parse(text + " UTC")
    return int(date.timestamp())

async def do_login(client: AsyncClient, username: str) -> None:
    privkey = crypto.DSAKey.gen()

    r = await client.get("/login")
    soup = BeautifulSoup(r.text, "html.parser")

    try:
        challenge = int(soup.select_one("input#challenge").get("value"))
    except:
        raise MumbleException("Missing / invalid login challenge")
    sig_r, sig_s = privkey.sign(challenge)

    data = {
        "name": username,
        "p": str(privkey.p),
        "q": str(privkey.q),
        "g": str(privkey.g),
        "y": str(privkey.y),
        "challenge": challenge,
        "signature": f"{sig_r},{sig_s}"
    }
    r = await client.post("/login", data=data)

    r = await client.get("/")
    soup = BeautifulSoup(r.text, "html.parser")
    error = soup.select_one("meta#notice")
    if error is not None:
        assert_equals(r.status_code, 200, "Register failed: " + error.get("content"))

    return privkey

async def do_launch(client: AsyncClient, wish: str) -> None:
    data = {
        "type": "firework",
        "x": str(random.uniform(0, 1)),
        "y": str(random.uniform(0, 1)),
        "wish": wish
    }
    r = await client.post("/launch", data=data)
    assert_equals(r.status_code, 200, "Launch failed: " + r.text)

async def do_profile(client: AsyncClient) -> None:
    r = await client.get("/profile")
    assert_equals(r.status_code, 200, "Invalid session")
    return r.text

@checker.putflag(0)
async def putflag(task: PutflagCheckerTaskMessage, logger: LoggerAdapter,
        client: AsyncClient, db: ChainDB) -> str:
    username = noise(10, 20)
    await do_login(client, username)

    await do_launch(client, task.flag)

    await db.set("info", client.cookies)

    return f"User {username}"

@checker.getflag(0)
async def getflag(task: GetflagCheckerTaskMessage,
        client: AsyncClient, db: ChainDB) -> None:
    try:
        cookies = await db.get("info")
    except KeyError:
        raise MumbleException("Database info missing")

    client.cookies = cookies
    text = await do_profile(client)

    assert_in(task.flag, text, "Flag missing")

@checker.putnoise(0)
async def putnoise(task: PutnoiseCheckerTaskMessage,
        client: AsyncClient, db: ChainDB) -> None:
    await do_login(client, noise(10, 20))

    wish = noise(20, 50)
    await do_launch(client, wish)

    await db.set("info", (client.cookies, wish))

@checker.getnoise(0)
async def getnoise_file(task: GetnoiseCheckerTaskMessage,
        client: AsyncClient, db: ChainDB, di: DependencyInjector) -> None:
    try:
        cookies, wish = await db.get("info")
    except KeyError:
        raise MumbleException("Database info missing")

    client.cookies = cookies
    text = await do_profile(client)

    assert_in(wish, text, "Noise missing")

@checker.exploit(0)
async def exploit_python_compare(task: ExploitCheckerTaskMessage, logger: LoggerAdapter,
        searcher: FlagSearcher, client: AsyncClient) -> Optional[str]:
    assert_equals(type(task.attack_info), str, "Attack info missing")
    assert_equals(len(task.attack_info.split()), 2, "Attack info invalid")
    username = task.attack_info.split()[1]

    await do_login(client, username)
    text = await do_profile(client)

    return searcher.search_flag(text)

# @checker.exploit(1)
# async def exploit_signing_vuln(task: ExploitCheckerTaskMessage,
#         logger: LoggerAdapter, searcher: FlagSearcher,
#         client: AsyncClient) -> Optional[str]:
#     assert_equals(type(task.attack_info), str, "Attack info missing")
#     assert_equals(len(task.attack_info.split()), 2, "Attack info invalid")
#     username = task.attack_info.split()[1]
# 
#     # TODO henning
# 
#     return None

if __name__ == "__main__":
    checker.run()
