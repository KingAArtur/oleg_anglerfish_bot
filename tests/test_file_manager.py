import pytest

from src.file_manager import FileManager


@pytest.fixture
def manager(tmp_path):
    return FileManager(dir_path=tmp_path)


def test_create_persistent_file(tmp_path, manager):
    filename = "save.txt"
    content = "uh huh"

    with manager.open(filename, tmp=False, mode="w") as file:
        file.write(content)

    with open(tmp_path / filename, encoding="utf-8") as file:
        content_from_file = "\n".join(file.readlines())

    assert content_from_file == content


def test_create_tmp_file(tmp_path, manager):
    filename = "save.txt"
    content = "uh huh"

    with manager.open(filename, tmp=True, mode="w") as file:
        file.write(content)

    with open(tmp_path / "tmp" / filename, encoding="utf-8") as file:
        content_from_file = "\n".join(file.readlines())

    assert content_from_file == content


def test_cleanup(tmp_path, manager):
    filename = "save.txt"
    content = "uh huh"

    with manager.open(filename, tmp=False, mode="w") as file:
        file.write(content)

    with manager.open(filename, tmp=True, mode="w") as file:
        file.write(content)

    file_persistent_path = tmp_path / filename
    file_tmp_path = tmp_path / "tmp" / filename

    assert file_persistent_path.exists()
    assert file_tmp_path.exists()

    manager.cleanup()

    assert file_persistent_path.exists()
    assert not file_tmp_path.exists()


def test_exists(tmp_path, manager):
    filename = "save.txt"
    content = "uh huh"

    with manager.open(filename, tmp=False, mode="w") as file:
        file.write(content)

    assert manager.exists(filename=filename, tmp=False)
    assert not manager.exists(filename="omg" + filename, tmp=False)
