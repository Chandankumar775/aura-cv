import io

import pytest

from aura.core.hashing import (
    ZERO_DIGEST,
    format_digest,
    is_digest,
    parse_digest,
    sha256_bytes,
    sha256_canonical,
    sha256_file,
    sha256_stream,
    short_digest,
)

# SHA-256("abc") from FIPS 180-2, Appendix B.1.
ABC = "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_known_vector():
    assert sha256_bytes(b"abc") == ABC


def test_file_and_stream_match_bytes(tmp_path):
    data = bytes(range(256)) * 10_000  # > 1 chunk
    p = tmp_path / "blob.bin"
    p.write_bytes(data)
    assert sha256_file(p) == sha256_bytes(data) == sha256_stream(io.BytesIO(data))


def test_format_and_parse():
    hexpart = ABC.split(":")[1]
    assert format_digest(hexpart.upper()) == ABC
    assert parse_digest(ABC) == hexpart
    assert is_digest(ABC) and is_digest(ZERO_DIGEST)
    assert short_digest(ABC) == hexpart[:12]


@pytest.mark.parametrize("bad", ["", "sha256:", "sha256:abc", "md5:" + "0" * 64, "sha256:" + "G" * 64, ABC.upper(), None, 5])
def test_malformed_digests_rejected(bad):
    assert not is_digest(bad)
    if isinstance(bad, str):
        with pytest.raises(ValueError):
            parse_digest(bad)


def test_canonical_digest_ignores_key_order_and_whitespace():
    assert sha256_canonical({"b": 1, "a": [1, 2]}) == sha256_canonical({"a": [1, 2], "b": 1})
    assert sha256_canonical({"a": 1}) == sha256_bytes(b'{"a":1}')
