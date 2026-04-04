from pathlib import Path
from contextlib import contextmanager


class FileManager:
    """Class for managing a directory that all files used by the bot should be in.
    All files in dir_path/tmp/* are meant to be temporary and files in dir_path/* are meant to be persistent
    """
    def __init__(self, dir_path: str | Path):
        if isinstance(dir_path, str):
            dir_path = Path(dir_path)

        if not dir_path.exists():
            dir_path.mkdir()
        if dir_path.is_file():
            raise FileExistsError(dir_path)

        dir_tmp_path = dir_path / "tmp"
        if not dir_tmp_path.exists():
            dir_tmp_path.mkdir()
        if dir_tmp_path.is_file():
            raise FileExistsError(dir_tmp_path)

        self.dir_path: Path = dir_path
        self.dir_tmp_path: Path = dir_tmp_path

    def _path(self, filename: str, tmp: bool) -> Path:
        return (self.dir_tmp_path if tmp else self.dir_path) / filename

    @contextmanager
    def open(self, filename: str, tmp: bool, mode: str = "r", encoding: str = "utf-8"):
        path = self._path(filename=filename, tmp=tmp)
        with open(path, mode=mode, encoding=encoding) as file:
            yield file

    def exists(self, filename: str, tmp: bool):
        return self._path(filename=filename, tmp=tmp).exists()

    def cleanup(self):
        for path in self.dir_tmp_path.iterdir():
            path.unlink()