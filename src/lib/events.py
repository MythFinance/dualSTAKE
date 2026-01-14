from pyteal import Log, Concat, Bytes
from Cryptodome.Hash import SHA512


def sha512_256(data):
    chksum = SHA512.new(truncate="256")
    chksum.update(data)
    return chksum.digest()


def arc28_header(event_definition):
    return Bytes(sha512_256(bytearray(event_definition, "utf-8"))[0:4])


def emit_event(event_definition, *args):
    return Log(Concat(arc28_header(event_definition), *args))
