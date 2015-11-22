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
    '-u', '--unstable', action='store_true', default=False,
    help="show unstable arches")
argparser.add_argument(
    '-c', '--collapse', action='store_true', default=False,
    help="show collapsed list of arches")
# TODO: check against valid arch list
argparser.add_argument(
    '-a', '--arch', action='extend_comma',
    help='arches to display')
# TODO: force ebuild repos only and allow multi-repo comma-separated input
argparser.add_argument(
    '-r', '--repo',
    action=commandline.StoreRepoObject, priority=29,
    help='repo(s) to use (defaults to all ebuild repos)')
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
    arches = known_arches
    if namespace.arch is not None:
        arches = arches.intersection(namespace.arch)
    if not namespace.collapse:
        prefix_arches = set(x for x in arches if '-' in x)
        native_arches = arches.difference(prefix_arches)
        arches = native_arches
        if namespace.unstable:
            arches = arches.union(prefix_arches)

    namespace.repo = repo
    namespace.known_arches = known_arches
    namespace.arches = arches


@argparser.bind_main_func
def main(options, out, err):
    for token, restriction in options.targets:
        pkgs = options.repo.match(restriction)

        if not pkgs:
            err.write("no matches for '%s'" % (token,))
            continue

        if options.collapse:
            keywords = []
            for pkg in pkgs:
                if options.unstable:
                    keywords.extend(x.lstrip('~') for x in pkg.keywords)
                else:
                    keywords.extend(pkg.keywords)
            arches = options.arches.intersection(keywords)
            out.write(' '.join(sorted(arches)))
        else:
            # TODO: tabular layout
            d = defaultdict(dict)
            for pkg in sorted(pkgs):
                out.write('{} | {} | {}'.format(pkg.fullver, ' '.join(pkg.keywords), pkg.repo.repo_id))
                d[pkg.slot][pkg.fullver] = pkg.keywords
