# Fireworx

Service for launching and viewing fireworks.

User authentication is done via challenge-response using DSA. Users
can launch fireworks with an optional wish every few seconds.

A log is kept of which fireworks were launched where and with what wish
that can be viewed by users on the profile page.

## Vulnerabilities

The signature $(1,0)$ passes `verify` for any public key and can be used
to login as the flag user.

A nonce-reuse in the key generation allows forging signatures and to login
as the flag user.

