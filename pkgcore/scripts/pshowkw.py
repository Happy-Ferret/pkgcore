# Copyright: 2015 Tim Harder <radhermit@gmail.com
# License: BSD/GPL2

"""Display keywords for specified targets."""

import argparse

from snakeoil.lists import unstable_unique

from pkgcore.util import commandline, parserestrict, repo_utils
from pkgcore.repository.util import RepositoryGroup
from pkgcore.scripts.pquery import RawAwareStoreRepoObject


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
    "--raw", action='store_true', default=False,
    help="use raw dependencies")
argparser.add_argument(
    '--unfiltered', action='store_true', default=False,
    help="With this option enabled, all license filtering, visibility filtering"
         " (ACCEPT_KEYWORDS, package masking, etc) is turned off.")
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
    action=RawAwareStoreRepoObject, priority=29,
    help='repo(s) to use (default from domain if omitted)')
argparser.add_argument(
    'targets', metavar='target', nargs='+', action=StoreTarget,
    help="extended atom matching of packages")


@argparser.bind_delayed_default(30, 'repos')
def setup_repos(namespace, attr):
    # Get repo(s) to operate on.
    if namespace.repo:
        repos = [namespace.repo]
    elif namespace.unfiltered:
        repos = namespace.domain.repos_configured.values()
    else:
        repos = namespace.domain.ebuild_repos

    if namespace.raw:
        repos = repo_utils.get_raw_repos(repos)

    setattr(namespace, attr, RepositoryGroup(repos))


@argparser.bind_final_check
def _validate_args(parser, namespace):
    arches = {arch for repo in namespace.repos.repos
              for arch in repo.config.known_arches}
    if namespace.arch is not None:
        arches = arches.intersection(namespace.arch)
    if namespace.unstable:
        arches = {'~' + arch for arch in arches}
    namespace.arches = arches


@argparser.bind_main_func
def main(options, out, err):
    for token, restriction in options.targets:
        pkgs = options.repos.match(restriction)

        if not pkgs:
            err.write("no matches for '%s'" % (token,))
            continue

        if options.stable or options.unstable:
            keywords = set(unstable_unique(arch for pkg in pkgs for arch in pkg.keywords))
            out.write(' '.join(sorted(keywords.intersection(options.arches))))
        else:
            for pkg in pkgs:
                out.write('%s: %s' % (pkg.cpvstr, ', '.join(pkg.keywords)))
