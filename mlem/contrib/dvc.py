import contextlib
from typing import IO, ClassVar, Iterator, Tuple
from urllib.parse import unquote_plus

from fsspec import AbstractFileSystem
from fsspec.implementations.github import GithubFileSystem

from mlem.core.artifacts import LocalArtifact, LocalStorage, Storage
from mlem.core.meta_io import get_fs


class DVCStorage(LocalStorage):
    """For now this storage is user-managed dvc storage, which means user should
    track corresponding files with dvc manually.
    TODO: add support for pipeline-tracked files and for single files with .dvc
     Also add possibility to automatically add and push every artifact"""

    type: ClassVar = "dvc"
    uri: str = ""

    def upload(self, local_path: str, target_path: str) -> "DVCArtifact":
        return DVCArtifact(uri=super().upload(local_path, target_path).uri)

    @contextlib.contextmanager
    def open(self, path) -> Iterator[Tuple[IO, "DVCArtifact"]]:
        with super().open(path) as (io, _):
            yield io, DVCArtifact(uri=path)

    def relative(self, fs: AbstractFileSystem, path: str) -> Storage:
        storage = super().relative(fs, path)
        if isinstance(storage, LocalStorage):
            return DVCStorage(uri=storage.uri)  # pylint: disable=no-member
        return storage


class DVCArtifact(LocalArtifact):
    type: ClassVar = "dvc"
    uri: str

    def download(self, target_path: str) -> LocalArtifact:
        from dvc.repo import Repo

        Repo.get_url(self.uri, out=target_path)
        return LocalArtifact(uri=target_path)

    @contextlib.contextmanager
    def open(self) -> Iterator[IO]:
        from dvc.api import open

        fs, path = get_fs(self.uri)
        # TODO: support other sources of dvc-tracked repos
        #  At least local and git
        if isinstance(fs, GithubFileSystem):
            with open(
                path,
                f"https://github.com/{fs.org}/{fs.repo}",
                unquote_plus(fs.root),
                mode="rb",
            ) as f:
                yield f
        else:
            with fs.open(path) as f:
                yield f

    def relative(self, fs: AbstractFileSystem, path: str) -> "DVCArtifact":
        relative = super().relative(fs, path)
        return DVCArtifact(uri=relative.uri)  # pylint: disable=no-member