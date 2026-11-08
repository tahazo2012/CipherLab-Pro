import pytest

from src.core.file_handler import FileHandlerError, load_file, read_file_bytes, write_bytes, write_text


def test_round_trip_text_and_bytes(tmp_path):
    p = tmp_path / "a.txt"
    write_text(p, "سلام 😀")
    lf = load_file(p)
    assert lf.kind == "txt" and lf.text == "سلام 😀"
    raw = bytes(range(256))
    write_bytes(tmp_path / "b.bin", raw)
    assert load_file(tmp_path / "b.bin").data == raw


def test_invalid_utf8_preserved_as_binary(tmp_path):
    p = tmp_path / "x.txt"
    p.write_bytes(b"\xff\xfe\x00bad")
    lf = load_file(p)
    assert lf.kind == "bin" and lf.text is None and lf.data == b"\xff\xfe\x00bad"


def test_kinds(tmp_path):
    for name, kind in (("a.hex", "hex"), ("a.json", "json"), ("a.weird", "bin")):
        (tmp_path / name).write_text("{}")
        assert load_file(tmp_path / name).kind == kind


def test_overwrite_requires_confirmation(tmp_path):
    p = tmp_path / "o.txt"
    write_text(p, "one")
    with pytest.raises(FileExistsError):
        write_text(p, "two")
    assert p.read_text() == "one"
    write_text(p, "two", overwrite=True)
    assert p.read_text() == "two"
    assert not list(tmp_path.glob(".cipherlab-*"))


def test_size_limit_and_bad_paths(tmp_path):
    p = tmp_path / "big.bin"
    p.write_bytes(b"x" * 100)
    with pytest.raises(FileHandlerError, match="limit"):
        read_file_bytes(p, max_bytes=50)
    with pytest.raises(FileHandlerError):
        read_file_bytes(tmp_path / "missing")
    with pytest.raises(FileHandlerError, match="not a regular file"):
        read_file_bytes(tmp_path)
    with pytest.raises(FileHandlerError, match="Refusing"):
        write_bytes(tmp_path / "w", b"x" * 20, max_bytes=10)
