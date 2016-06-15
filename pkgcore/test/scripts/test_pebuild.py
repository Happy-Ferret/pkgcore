# Copyright: 2006 Marien Zwart <marienz@gentoo.org>
# License: BSD/GPL2

from pkgcore.scripts import pebuild
from pkgcore.test import TestCase
from pkgcore.test.scripts.helpers import ArgParseMixin


class CommandlineTest(TestCase, ArgParseMixin):

    _argparser = pebuild.argparser

    suppress_domain = True

    def test_parser(self):
        self.assertError('the following arguments are required: <atom|ebuild>, phase')
        self.assertError('the following arguments are required: phase', 'dev-util/diffball')
        self.assertEqual(self.parse('foo/bar', 'baz', 'spork').phase, ['baz', 'spork'])
