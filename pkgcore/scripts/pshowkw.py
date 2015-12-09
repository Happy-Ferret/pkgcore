# Copyright: 2015 Tim Harder <radhermit@gmail.com
# License: BSD/GPL2

"""display ebuild keywords"""

import argparse
from functools import partial

from pkgcore.util import commandline, parserestrict

from snakeoil.demandload import demandload

demandload(
    'os',
    'pkgcore.repository:multiplex',
)


argparser = commandline.mk_argparser(description=__doc__)
arch_options = argparser.add_argument_group('arch options')
arch_options.add_argument(
    '-u', '--unstable', action='store_true',
    help="show unstable arches")
arch_options.add_argument(
    '-p', '--prefix', action='store_true',
    help="show prefix and non-native arches")
arch_options.add_argument(
    '-c', '--collapse', action='store_true',
    help="show collapsed list of arches")
arch_options.add_argument(
    '-a', '--arch', action='extend_comma',
    help='select arches to display')

# TODO: force ebuild repos only and allow multi-repo comma-separated input
argparser.add_argument(
    '-r', '--repo',
    action=commandline.StoreRepoObject, priority=29,
    help='repo(s) to use (defaults to all ebuild repos)')

argparser.add_argument(
    'targets', metavar='target', nargs='*',
    action=partial(commandline.StoreTarget, sets=False),
    help="extended atom matching of packages")


@argparser.bind_delayed_default(30, 'repos')
def setup_repos(namespace, attr):
    # Get repo(s) to operate on.
    if namespace.repo:
        repos = [namespace.repo.raw_repo]
        repo = multiplex.tree(*repos)
    else:
        repo = namespace.domain.all_raw_ebuild_repos

    # build arch sets
    known_arches = {arch for r in repo.trees
                    for arch in r.config.known_arches}
    arches = known_arches
    if namespace.arch is not None:
        selected_arches = set(namespace.arch)
        unknown_arches = selected_arches.difference(known_arches)
        if unknown_arches:
            argparser.error(
                'unknown arch(es): %s (choices: %s)' % (
                    ', '.join(sorted(unknown_arches)), ', '.join(sorted(known_arches))))
        arches = arches.intersection(selected_arches)
    prefix_arches = set(x for x in arches if '-' in x)
    native_arches = arches.difference(prefix_arches)
    arches = native_arches
    if namespace.prefix:
        arches = arches.union(prefix_arches)

    namespace.repo = repo
    namespace.known_arches = known_arches
    namespace.prefix_arches = prefix_arches
    namespace.native_arches = native_arches
    namespace.arches = arches


@argparser.bind_final_check
def _validate_args(parser, namespace):
    # allow no args if we're in a repo, obviously it'll work faster if we're in
    # an invididual ebuild dir but we're not that restrictive
    if not namespace.targets:
        try:
            restriction = namespace.repo.path_restrict(os.getcwd())
        except ValueError as e:
            parser.error('missing target argument and not in a configured repo directory')

        namespace.targets = [(os.getcwd(), restriction)]


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
            out.write(' '.join(
                sorted(arches.intersection(options.native_arches)) +
                sorted(arches.intersection(options.prefix_arches))))
        else:
            # TODO: tabular layout
            for pkg in sorted(pkgs):
                out.write('{}: {}'.format(pkg.fullver, ' '.join(pkg.keywords)))
