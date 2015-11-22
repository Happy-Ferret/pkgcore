# Copyright: 2015 Tim Harder <radhermit@gmail.com
# License: BSD/GPL2

"""Display keywords for specified targets."""

import argparse

from snakeoil.lists import unstable_unique

from pkgcore.util import commandline, parserestrict
from pkgcore.repository.util import RepositoryGroup


class StoreTarget(argparse._AppendAction):

    def __call__(self, parser, namespace, values, option_string=None):
        targets = []
        try:
            for x in values:
                targets.append((x, parserestrict.parse_match(x)))
        except parserestrict.ParseError as e:
            parser.only_error(e)
        setattr(namespace, self.dest, targets)


argparser = commandline.mk_argparser(description=__doc__)
argparser.add_argument(
    '-s', '--stable', action='store_true', default=False,
    help="show collapsed list of stable keywords")
argparser.add_argument(
    '-u', '--unstable', action='store_true', default=False,
    help="show collapsed list of unstable keywords")
argparser.add_argument(
    '-a', '--arch', action='extend_comma',
    help='arches to display')
argparser.add_argument(
    '-r', '--repo',
    action=commandline.StoreRepoObject, priority=29,
    help='repo(s) to use (default from domain if omitted)')
argparser.add_argument(
    'targets', metavar='target', nargs='+', action=StoreTarget,
    help="extended atom matching of packages")


@argparser.bind_delayed_default(30, 'repos')
def setup_repos(namespace, attr):
    # Get repo(s) to operate on.
    if namespace.repo:
        repo = RepositoryGroup([namespace.repo.raw_repo])
    else:
        repo = namespace.domain.ebuild_repos_raw

    known_arches = {arch for r in repo.repos
                    for arch in r.config.known_arches}
    stable = set()
    unstable = set()
    arches = known_arches
    if namespace.arch is not None:
        arches = arches.intersection(namespace.arch)
    if namespace.stable:
        stable = arches
    if namespace.unstable:
        unstable = {'~' + arch for arch in arches}

    namespace.repo = repo
    namespace.known_arches = known_arches
    namespace.arches = stable | unstable


@argparser.bind_main_func
def main(options, out, err):
    for token, restriction in options.targets:
        pkgs = options.repo.match(restriction)

        if not pkgs:
            err.write("no matches for '%s'" % (token,))
            continue

        if options.stable or options.unstable:
            keywords = set(unstable_unique(arch for pkg in pkgs for arch in pkg.keywords))
            keywords = sorted(keywords.intersection(options.arches))
            if keywords:
                out.write(' '.join(keywords))
        else:
            for pkg in pkgs:
                out.write('%s: %s' % (pkg.cpvstr, ', '.join(pkg.keywords)))
