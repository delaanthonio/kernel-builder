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
from subprocess import CompletedProcess
from typing import Optional

from kbuilder.core.make import make, make_output
from cached_property import cached_property
from unipath.path import Path
from kbuilder.core.kbuild_image import KbuildImage
from kbuilder.core.arch import Arch

KERNEL_DIRS = ['arch', 'crypto', 'Documentation', 'drivers', 'include',
               'scripts', 'tools']


class Kernel(object):
    """store info for a kernel."""
    def __init__(self, root: str, *, arch: Arch=None,
                 defconfig: str='defconfig') -> None:
        """Initialze a new Kernel.

        Positional arguments:
            root -- kernel root directory.

        Keyword arguments:
            arch -- kernel architecture.
            defconfig -- default configuration file.
        """
        self._root = Path(root)
        self._release_version = self.version
        self._extra_version = None
        self._defconfig = defconfig
        self._arch = arch
        self._kbuild_image = KbuildImage[self.arch.name].value

    @property
    def root(self):
        """The absolute path of the kernel root"""
        return self._root

    @property
    def name(self):
        """The name of the kernel root"""
        return self.root.name

    @cached_property
    def version(self):
        """The local kernel version in the defconfig file."""
        return self._find_kernel_version()

    @property
    def extra_version(self):
        """An optional version to append to the end of the kernel version."""
        return self._extra_version

    @extra_version.setter
    def extra_version(self, version: str):
        """Set extra_version."""
        self._extra_version = version

    @property
    def release_version(self):
        """Version of the kernel release.

        If extraversion is defined, then it will be contatened.
        """
        if self.extra_version:
            return '{0.version}-{0.extra_version}'.format(self)
        return self.version

    @property
    def arch(self):
        """The architecture of the kernel."""
        return self._arch

    @property
    def defconfig(self):
        """The default configuration file.

        The defconfig file specifies which modules to build for the kernel."""
        return self._defconfig

    @property
    def kbuild_image(self):
        """The absolute path to the compressed kernel image."""
        return self.root.child('arch', self.arch.name, 'boot', self._kbuild_image)

    def _find_kernel_verion(self):
        with self:
            output = make_output('kernelrelease').rstrip()
            lines = output.split('\n')
            kernelrelease = lines[-1]
            return kernelrelease[8:]

    def __enter__(self):
        self._prev_dir = Path(os.getcwd())
        self.root.chdir()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._prev_dir.chdir()
        return False

    @staticmethod
    def find_root(initial_path: str) -> Path:
        """Find the root of the kernel directory.

        Search for the root of a kernel directory starting at a given directory.
        The search continues until the kernel root is found or the system root
        directory is reached. If the system root directory is reached, then
        'None' is returned. Otherwise, the path of the kernel root directory is
        returned.
        Arguments
        initial_path -- the path to begin search
        """
        def is_kernel_root(path: Path) -> bool:
            """Check if the current path is the root directory of a kernel."""
            files_in_dir = [file.name for file in os.scandir(path)]
            return all(kernel_dir in files_in_dir for kernel_dir in KERNEL_DIRS)

        def walk_to_root(path: Path) -> Path:
            """Search for the root of the kernel directory."""
            system_root = Path('/')
            if is_kernel_root(path):
                return path
            elif path == system_root:
                return None
            else:
                return walk_to_root(path.parent)

        return walk_to_root(Path(initial_path))

    @staticmethod
    def arch_clean() -> CompletedProcess:
        """Remove compiled kernel files in the arch directory.

        This form of cleaning is useful for rebuilding the kernel with the same
        Toolchain, since only files that were changed will be compiled.
        Keyword arguements
        """
        print('Performing an arch clean')
        return make('archclean')

    @staticmethod
    def clean() -> CompletedProcess:
        """Remove all compiled kernel files.

        This form of cleaning is useful when switching the toolchain to build
        kernel since all files need to be recompiled.
        Keyword arguements
        """
        print('Removing all compiled files')
        return make('clean')

    def make_defconfig(self) -> None:
        """Make the default configuration file."""
        make(self.defconfig)

    def build_kbuild_image(self, log_dir: Optional[str]=None) -> Path:
        """Make the kbuild image.

        Keyword arguments:
            log_dir -- the directory of the build log file

        Precondition:
            self.arch is set

        Returns:
            the absolute path of kbuild image on successful build.
        """
        Path(log_dir).mkdir()
        build_log = Path(log_dir, self.release_version + '-log.txt')
        output = make_output('all')
        build_log.write_file(output)
        return self.kbuild_image
