#!/usr/bin/env python

"sets up one of the tnt components"

import os
import sys

from distutils.core import setup

def main():
    setup(
          name = "urwid_form",
          description = "a quick tool for gathering form data",
          version = '0.1',
          packages = ['urwid_form'],
          package_dir = {'urwid_form': 'src'},
          author = "Peter Banka",
          author_email = 'peter.banka@gmail.com',
          long_description = 'a simple tool to build urwid forms to fill out data',
          scripts = ['scripts/form_test.py'],
          provides = 'urwid_form',
          classifiers = [
             "Development Status :: 2 - Pre-Alpha",
             "Programming Language :: Python",
             "Operating System :: POSIX",
             "Topic :: Software Development :: Libraries :: Python Modules",
          ],
         )

if __name__ == "__main__":
    main()
