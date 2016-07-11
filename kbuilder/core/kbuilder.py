

import os
import shutil
import sys
from subprocess import check_call
from typing import Iterable

import arrow
import kbuilder.core.make as mk
from kbuilder.core import gcc
from kbuilder.core.arch import Arch
from kbuilder.core.gcc import Toolchain
from kbuilder.core.kernel import Kernel
from kbuilder.core.kernel_android import AndroidKernel
from kbuilder.core.messages import alert, highlight, success
from unipath import Path

VERSION = '{0}.{1}'.format(*sys.version_info[:2])

if VERSION < '3.5':
    print(alert('Python 3.5+ is required'))
    exit()


# The root of the kernel
KERNEL_ROOT_DIR = str(Kernel.find_root(os.getcwd()))
print(KERNEL_ROOT_DIR)

# This dirctory should contain the necessary tools for creating the kernel
RESOURSES_DIR = Path(KERNEL_ROOT_DIR, 'android', 'ota')

# The directory to export the package zip
DEF_EXPORT_DIR = Path(KERNEL_ROOT_DIR, '..', 'output').norm()

TOOLCHAIN_DIR = Path(KERNEL_ROOT_DIR, '..', 'toolchains').norm()

SUBLIME_N9_EXPORT_DIR = Path(os.getenv('SUBLIME_N9_EXPORT_DIR'))

# Directory for build logs
LOG_DIR = Path(DEF_EXPORT_DIR, 'build_logs')


def get_export_dir() -> str:
    """Return the directory to export the kernel."""
    if SUBLIME_N9_EXPORT_DIR:
        return SUBLIME_N9_EXPORT_DIR
    else:
        return DEF_EXPORT_DIR


def export_file(file_export: str, export_dir: str) -> None:
    """Send a file to the export directory.

    Keyword arguments:
    file_export -- the absolute path of the file to export
    export_dir -- the directory to export the file
    """
    file_path = Path(file_export)
    Path(export_dir).mkdir()
    check_call('mv {} {}'.format(file_path, export_dir), shell=True)
    print(success('{} exported to {}'.format(file_path.name, export_dir)))


def time_delta(func) -> None:
    """Time how long it takes to run a function."""
    def args_wrapper(*args, **kw_args):
        start_time = arrow.utcnow().timestamp
        func(*args, **kw_args)
        end_time = arrow.utcnow().timestamp
        time_delta = end_time - start_time
        minutes = highlight(time_delta // 60)
        seconds = highlight(time_delta % 60)
        print('Time passed: {} minute(s) and {} second(s)'.format(minutes,
                                                                  seconds))
    return args_wrapper


@time_delta
def build(kernel: Kernel, toolchains: Iterable[Toolchain],
          defconfig: str='defconfig', export_dir: str=None,
          ota_package_dir: str=None, log_dir: str=None) -> None:
    """Build the kernel with the given toolchains."""
    print('making: ' + highlight(defconfig))
    mk.make(defconfig)
    for toolchain in toolchains:
        with toolchain:
            kernel.arch_clean()
            kbuild_image, _ = kernel.build_kbuild_image(toolchain,
                                                        log_dir=log_dir)
            if ota_package_dir:
                shutil.copy(kbuild_image, ota_package_dir + '/boot')
                kernel.make_ota_package(output_dir=export_dir,
                                        source_dir=ota_package_dir,
                                        extra_version=toolchain.name)


def main():
    """Build the kernel with the selected toolchains."""
    toolchains = gcc.scandir(TOOLCHAIN_DIR)
    toolchains = gcc.select(toolchains)
    with AndroidKernel(KERNEL_ROOT_DIR, Arch.arm64) as kernel:
        export_path = Path(get_export_dir(), kernel.version_numbers)
        DEF_EXPORT_DIR.mkdir(parents=True)
        build(kernel, toolchains, defconfig='defconfig', export_dir=export_path,
              ota_package_dir=RESOURSES_DIR, log_dir=LOG_DIR)


if __name__ == '__main__':
    main()
