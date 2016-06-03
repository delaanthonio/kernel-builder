#     Copyright (C) 2016 Dela Anthonio <dell.anthonio@gmail.com>
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from typing import Iterable, List, Optional

from unipath.path import Path

from kbuilder.core.messages import alert, highlight, success
from kbuilder.core.arch import Arch


class Toolchain(object):
    """Store relevant info of a toolchain."""

    compiler_prefixes = {'aarch64': Arch.arm64, 'arm-eabi': Arch.arm}

    def __init__(self, root: str) -> None:
        """Initialize a new Toolchain.

        Keyword arguments:
        root -- the root directory of the toolchain
        """
        self.root = Path(root)
        self._name = self.root.name
        self._compiler_prefix = Path(self.find_compiler_prefix())
        self._target_arch = self._find_target_arch()

    def __str__(self) -> str:
        """Return the name of the toolchain's root directory."""
        return self.name

    def __nonzero__(self) -> bool:
        """Return whether the toolchain is valid.

        A toolchain needs a 'bin' directory to be valid.
        """
        return self.root.isdir() and Path(self.root, 'bin').isdir()

    def __enter__(self):
        """Set this self as the toolchain to compile targets."""
        self.set_as_active()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Do not supresses any errors.

        Positional arguments:
        exc_type -- the type of exception
        exc_val -- the value of the exception
        exc_tb -- the traceback of the exception
        """
        return False

    @property
    def name(self):
        """The name of this."""
        return self._name

    @property
    def target_arch(self):
        """The target architecture of this compiler."""
        return self._target_arch

    @property
    def compiler_prefix(self):
        """The prefix of all binaries of this."""
        return self._compiler_prefix

    def find_compiler_prefix(self) -> str:
        """Return the prefix of all binaries of this."""
        def find_binaries() -> Iterable:
            """Return an Iterable of binaries in the toolchain's bin folder."""
            try:
                return os.scandir(self.root.child('bin'))
            except:
                pass

        def is_gcc_binary(binary_name: str) -> bool:
            return binary_name.endswith('gcc')

        for entry in find_binaries():
            if is_gcc_binary(entry.name):
                compiler_prefix = entry.path[:-3]
                return compiler_prefix

    def _find_target_arch(self) -> Arch:
        """Determine the target architecture of the toolchain."""
        prefix = self.compiler_prefix.name
        for arch_prefix in iter(Toolchain.compiler_prefixes):
            if prefix.startswith(arch_prefix):
                target_arch = Toolchain.compiler_prefixes[arch_prefix]
                return target_arch

    def set_as_active(self):
        """Set this self as the active toolchain to compile with."""
        os.putenv('CROSS_COMPILE', self.compiler_prefix)
        os.putenv('SUBARCH', self.target_arch.name)


def scandir(toolchain_dir: str,
            target_arch: Optional[Arch]=None) -> List[Toolchain]:
    """Return a list of toolchains located in a directory.

    A toolchain is considered valid if it has a gcc executable in its
     'bin' directory.

    Positional arguments:
    toolchain_dir -- the directory to look for toolchains.

    Keyword arguments:
    target_arch -- the target architecture of toolchains to search for.
        If empty, then toolchains of any architecture may be returned
        otherwise only toolchains with the matching architecture will be
        returned (default None).
    """
    def valid_arch():
        return not target_arch or toolchain.target_arch == target_arch
    toolchains = []
    entries = sorted(os.scandir(toolchain_dir), key=lambda x: x.name)

    for entry in entries:
        toolchain = Toolchain(entry.path)
        if toolchain and valid_arch():
            toolchains.append(toolchain)
    return toolchains


def select(toolchains: List[Toolchain]) -> Iterable[Toolchain]:
    """Return an Iterator of toolchains from a list of toolchains.

    Each toolchain will be printed with its position in the list.
    The positions begin at 1 and are printed next to the toolchain.
    Then the client will be prompted to enter in a series of numbers.
    An Iterable containing toolchains with the matching positions from the
    input will be returned. If only one toolchain is in the list,
    then it will be automatically selected.

    Positional arguments:
    toolchains -- the list of toolchains to select from
    """
    if len(toolchains) <= 1:
        return toolchains

    for index, toolchain in enumerate(toolchains, 1):
        print('{}) {}'.format(index, highlight(toolchain)))

    numbers = input('Enter numbers separated by spaces: ')
    chosen_numbers = [int(x) for x in numbers.split()]
    for number in chosen_numbers:
        yield toolchains[number - 1]
