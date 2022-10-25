# Fireworx

Service for launching and viewing fireworks.

User authentication is done via challenge-response using DSA. Users
can launch fireworks with an optional wish (flagstore #1) every few seconds.

A log is kept of which fireworks were launched where and with what wish,
that can be viewed by users on the profile page.

## Vulnerabilities

A nonce-reuse in the challenge-response allows forging signatures for the
flag user.

A bug in the database query during login allows logging in as another
user simply by supplying a different signing key.

