"""Sample lambda handler with all the 3.12 hazards."""
from collections import Mapping, MutableMapping  # deprecated
from distutils.util import strtobool            # removed in 3.12
import imp                                      # removed in 3.12
import asyncio
import datetime
import pkg_resources


@asyncio.coroutine   # removed in 3.11
def old_style():
    yield from asyncio.sleep(0)


def handler(event, context):
    now = datetime.datetime.utcnow()            # deprecated in 3.12
    loop = asyncio.get_event_loop()             # deprecated if no running loop
    info: Mapping = {}
    cfg: MutableMapping = {}
    version = pkg_resources.get_distribution("foo").version
    return {"ok": True, "ts": now.isoformat(), "cfg": cfg, "version": version}