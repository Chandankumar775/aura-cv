"""RFC 8785 conformance, using the RFC's own test vectors."""

import json
import struct

import pytest
from pydantic import BaseModel

from aura.core.canonical import CanonicalizationError, canonicalize, canonicalize_json_text

# RFC 8785 Appendix B: IEEE-754 bit patterns -> expected serialisation.
NUMBER_VECTORS = [
    ("0000000000000000", "0"),
    ("8000000000000000", "0"),  # minus zero
    ("0000000000000001", "5e-324"),
    ("8000000000000001", "-5e-324"),
    ("7fefffffffffffff", "1.7976931348623157e+308"),
    ("ffefffffffffffff", "-1.7976931348623157e+308"),
    ("4340000000000000", "9007199254740992"),
    ("c340000000000000", "-9007199254740992"),
    ("4430000000000000", "295147905179352830000"),
    ("44b52d02c7e14af5", "9.999999999999997e+22"),
    ("44b52d02c7e14af6", "1e+23"),
    ("44b52d02c7e14af7", "1.0000000000000001e+23"),
    ("444b1ae4d6e2ef4e", "999999999999999700000"),
    ("444b1ae4d6e2ef4f", "999999999999999900000"),
    ("444b1ae4d6e2ef50", "1e+21"),
    ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),
    ("3eb0c6f7a0b5ed8d", "0.000001"),
    ("41b3de4355555553", "333333333.3333332"),
    ("41b3de4355555554", "333333333.33333325"),
    ("41b3de4355555555", "333333333.3333333"),
    ("41b3de4355555556", "333333333.3333334"),
    ("41b3de4355555557", "333333333.33333343"),
    ("becbf647612f3696", "-0.0000033333333333333333"),
    ("43143ff3c1cb0959", "1424953923781206.2"),
]


def _double(hex_bits: str) -> float:
    return struct.unpack(">d", bytes.fromhex(hex_bits))[0]


@pytest.mark.parametrize("bits,expected", NUMBER_VECTORS)
def test_number_serialisation(bits, expected):
    assert canonicalize(_double(bits)) == expected.encode()


@pytest.mark.parametrize("bits", ["7fffffffffffffff", "7ff0000000000000", "fff0000000000000"])
def test_nan_and_infinity_rejected(bits):
    with pytest.raises(CanonicalizationError):
        canonicalize(_double(bits))


def test_rfc_section_3_2_2_example():
    text = r'''{
      "numbers": [333333333.33333329, 1E30, 4.50, 2e-3, 0.000000000000000000000000001],
      "string": "\u20ac$\u000F\u000aA'\u0042\u0022\u005c\\\"\/",
      "literals": [null, true, false]
    }'''
    # Expected output copied from RFC 8785 \u00a73.2.2 (raw strings keep its escapes literal).
    expected = (
        r'{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        r'"string":"' + "\u20ac" + r'$\u000f\nA' + "'" + r'B\"\\\\\"/"}'
    )
    assert canonicalize_json_text(text) == expected.encode("utf-8")


def test_rfc_section_3_2_3_sorting_by_utf16_code_units():
    text = r'''{
      "\u20ac": "Euro Sign",
      "\r": "Carriage Return",
      "\ufb33": "Hebrew Letter Dalet With Dagesh",
      "1": "One",
      "\ud83d\ude00": "Emoji: Grinning Face",
      "\u0080": "Control",
      "\u00f6": "Latin Small Letter O With Diaeresis"
    }'''
    keys = list(json.loads(canonicalize_json_text(text).decode("utf-8")).keys())
    assert keys == ["\r", "1", "\u0080", "\u00f6", "\u20ac", "\U0001F600", "\ufb33"]


def test_nested_ordering_and_no_whitespace():
    assert canonicalize({"b": {"z": 1, "y": [3, {"k": None}]}, "a": True}) == b'{"a":true,"b":{"y":[3,{"k":null}],"z":1}}'


def test_integer_safe_range():
    assert canonicalize(2**53 - 1) == b"9007199254740991"
    with pytest.raises(CanonicalizationError):
        canonicalize(2**53)


def test_rejects_non_json_types():
    with pytest.raises(CanonicalizationError):
        canonicalize({1: "int key"})
    with pytest.raises(CanonicalizationError):
        canonicalize({"s": {1, 2}})
    with pytest.raises(CanonicalizationError):
        canonicalize({"b": b"bytes"})


def test_pydantic_models_and_tuples_normalised():
    class M(BaseModel):
        y: int
        x: tuple[int, int]

    assert canonicalize(M(y=1, x=(2, 3))) == b'{"x":[2,3],"y":1}'
