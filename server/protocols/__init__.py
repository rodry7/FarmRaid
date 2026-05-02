from typing import Any

from protocols.base import BaseProtocol
from protocols.custom_http import CustomHTTPProtocol
from protocols.custom_tcp import CustomTCPProtocol
from protocols.faust import FAUSTProtocol
from protocols.forcad_http import ForcadHTTPProtocol
from protocols.forcad_tcp import ForcadTCPProtocol
from protocols.ructfe_http import RuCTFEHTTPProtocol
from protocols.volgactf import VolgaCTFProtocol

PROTOCOLS: dict[str, type[BaseProtocol]] = {
    "forcad_tcp": ForcadTCPProtocol,
    "forcad_http": ForcadHTTPProtocol,
    "ructfe_http": RuCTFEHTTPProtocol,
    "faust": FAUSTProtocol,
    "volgactf": VolgaCTFProtocol,
    "custom_http": CustomHTTPProtocol,
    "custom_tcp": CustomTCPProtocol,
}

PROTOCOL_INFO: list[dict[str, Any]] = [
    {
        "name": cls.name,
        "display_name": cls.display_name,
        "params_schema": cls.params_schema,
    }
    for cls in PROTOCOLS.values()
]


def get_protocol(name: str, params: dict[str, Any]) -> BaseProtocol:
    cls = PROTOCOLS.get(name)
    if cls is None:
        raise ValueError(f"Unknown protocol: {name!r}. Available: {list(PROTOCOLS)}")
    return cls(params)
