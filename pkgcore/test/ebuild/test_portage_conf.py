# Copyright: 2015 Tim Harder
# License: GPL2/BSD

import os
import shutil
import stat
from tempfile import NamedTemporaryFile
import textwrap

from snakeoil.osutils import pjoin
from snakeoil.test import TestCase
from snakeoil.test.mixins import TempDirMixin

from pkgcore import const
from pkgcore.config import errors
from pkgcore.ebuild.portage_conf import load_make_conf, load_repos_conf


class TestPortageConfig(TempDirMixin, TestCase):

    def __init__(self, *args, **kwargs):
        TempDirMixin.__init__(self, *args, **kwargs)
        TestCase.__init__(self, *args, **kwargs)

        # default files
        self.make_globals = {}
        load_make_conf(
            self.make_globals, pjoin(const.CONFIG_PATH, 'make.globals'))

        self.global_repos_defaults, self.global_repos_conf = load_repos_conf(
            pjoin(const.CONFIG_PATH, 'repos.conf'))

    def test_load_make_conf(self):
        self.assertIn('PORTAGE_TMPDIR', self.make_globals)

        # nonexistent file
        d = {}
        # by default files are required
        self.assertRaises(
            errors.ParsingError, load_make_conf,
            d, pjoin(self.dir, 'make.globals'))
        # should return empty dict when not required
        load_make_conf(d, pjoin(self.dir, 'make.conf'), required=False)
        self.assertEqual({}, d)

        # unreadable file
        d = {}
        with NamedTemporaryFile() as f:
            os.chmod(f.name, stat.S_IWUSR)
            self.assertRaises(
                errors.PermissionDeniedError, load_make_conf, d, f.name)

        # overrides and incrementals
        with NamedTemporaryFile() as f:
            f.write(b'DISTDIR=foo\nACCEPT_LICENSE=foo\n')
            f.flush()
            d = {}
            load_make_conf(d, pjoin(const.CONFIG_PATH, 'make.globals'))
            load_make_conf(d, f.name, allow_sourcing=True, incrementals=True)
            self.assertEqual('foo', d['DISTDIR'])
            self.assertEqual(
                ' '.join([self.make_globals['ACCEPT_LICENSE'], 'foo']),
                d['ACCEPT_LICENSE'])

    def test_load_make_conf_dir(self):
        # load files from dir and symlinked dir

        make_conf_dir = pjoin(self.dir, 'make.conf')
        os.mkdir(make_conf_dir)
        make_conf_sym = pjoin(self.dir, 'make.conf.sym')
        os.symlink(make_conf_dir, make_conf_sym)

        with open(pjoin(make_conf_dir, 'a'), 'w') as f:
            f.write('DISTDIR=foo\n')
            f.flush()

            d = {}
            load_make_conf(d, pjoin(const.CONFIG_PATH, 'make.globals'))
            sym_d = d.copy()
            load_make_conf(d, make_conf_dir)
            load_make_conf(sym_d, make_conf_sym)

            self.assertEqual(d, sym_d)
            self.assertEqual(
                self.make_globals['ACCEPT_LICENSE'], d['ACCEPT_LICENSE'])
            self.assertEqual('foo', d['DISTDIR'])

    def test_load_repos_conf(self):
        self.assertIn('gentoo', self.global_repos_conf)

        # nonexistent file
        self.assertRaises(
            errors.ParsingError, load_repos_conf,
            pjoin(self.dir, 'repos.conf'))

        # unreadable file
        with NamedTemporaryFile() as f:
            os.chmod(f.name, stat.S_IWUSR)
            self.assertRaises(
                errors.PermissionDeniedError, load_repos_conf, f.name)

        # blank file
        with NamedTemporaryFile() as f:
            self.assertRaises(
                errors.ConfigurationError, load_repos_conf, f.name)

        # missing location parameter
        with NamedTemporaryFile() as f:
            f.write(textwrap.dedent('''\
                [foo]
                sync-uri = git://foo.git''').encode())
            f.flush()
            self.assertRaises(
                errors.ParsingError, load_repos_conf, f.name)

        # bad priority value
        with NamedTemporaryFile() as f:
            f.write(textwrap.dedent('''\
                [foo]
                priority = foo
                location = /var/gentoo/repos/foo''').encode())
            f.flush()
            self.assertRaises(
                errors.ParsingError, load_repos_conf, f.name)

        # undefined main repo with 'gentoo' missing
        with NamedTemporaryFile() as f:
            f.write(textwrap.dedent('''\
                [foo]
                location = /var/gentoo/repos/foo''').encode())
            f.flush()
            self.assertRaises(
                errors.ConfigurationError, load_repos_conf, f.name)

        # default section isn't required as long as gentoo repo exists
        with NamedTemporaryFile() as f:
            f.write(textwrap.dedent('''\
                [foo]
                location = /var/gentoo/repos/foo
                [gentoo]
                location = /var/gentoo/repos/gentoo''').encode())
            f.flush()
            defaults, repos = load_repos_conf(f.name)
            self.assertEqual('gentoo', defaults['main-repo'])
            self.assertEqual(['foo', 'gentoo'], repos.keys())

    def test_load_repos_conf_dir(self):
        # repo priority sorting and dir/symlink scanning

        repos_conf_dir = pjoin(self.dir, 'repos.conf')
        os.mkdir(repos_conf_dir)
        repos_conf_sym = pjoin(self.dir, 'repos.conf.sym')
        os.symlink(repos_conf_dir, repos_conf_sym)

        # add global repos.conf
        shutil.copyfile(
            pjoin(const.CONFIG_PATH, 'repos.conf'),
            pjoin(repos_conf_dir, 'repos.conf'))

        with open(pjoin(repos_conf_dir, 'z'), 'w') as f:
            f.write(textwrap.dedent('''\
                [bar]
                location = /var/gentoo/repos/bar

                [foo]
                location = /var/gentoo/repos/foo
                priority = 10'''))
            f.flush()

        defaults, repos = load_repos_conf(repos_conf_dir)
        sym_defaults, sym_repos = load_repos_conf(repos_conf_sym)

        self.assertEqual(defaults, sym_defaults)
        self.assertEqual(repos, sym_repos)
        self.assertEqual('gentoo', defaults['main-repo'])
        self.assertEqual(['foo', 'bar', 'gentoo'], repos.keys())
