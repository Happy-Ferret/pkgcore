# Copyright: 2015 Tim Harder <radhermit@gmail.com
# License: BSD/GPL2

"""display ebuild keywords"""

from functools import partial

from pkgcore.util import commandline

from snakeoil.demandload import demandload

demandload(
    'os',
    'pkgcore.ebuild:repository@ebuild_repo',
    'pkgcore.repository:multiplex',
)


argparser = commandline.ArgumentParser(description=__doc__)
arch_options = argparser.add_argument_group('arch options')
arch_options.add_argument(
    '-s', '--stable', action='store_true',
    help='show stable arches')
arch_options.add_argument(
    '-u', '--unstable', action='store_true',
    help='show unstable arches')
arch_options.add_argument(
    '-o', '--only-unstable', action='store_true',
    help='show arches that only have unstable keywords')
arch_options.add_argument(
    '-p', '--prefix', action='store_true',
    help='show prefix and non-native arches')
arch_options.add_argument(
    '-c', '--collapse', action='store_true',
    help='show collapsed list of arches')
arch_options.add_argument(
    '-a', '--arch', action='extend_comma',
    help='select arches to display')

# TODO: force ebuild repos only and allow multi-repo comma-separated input
argparser.add_argument(
    '-r', '--repo',
    action=commandline.StoreRepoObject, raw=True, priority=29,
    help='repo(s) to use (defaults to all ebuild repos)')

argparser.add_argument(
    'targets', metavar='target', nargs='*',
    action=partial(commandline.StoreTarget, sets=False),
    help='extended atom matching of packages')


@argparser.bind_delayed_default(30, 'repos')
def setup_repos(namespace, attr):
    # Get repo(s) to operate on.
    repo = namespace.repo
    if repo:
        # TODO: remove this workaround once StoreRepoObject accepts types
        if not isinstance(repo, ebuild_repo._UnconfiguredTree):
            argparser.error('only ebuild repos are supported')
        repo = multiplex.tree(repo)
    else:
        repo = namespace.domain.all_raw_ebuild_repos
    namespace.repo = repo


@argparser.bind_delayed_default(40, 'arches')
def setup_arches(namespace, attr):
    known_arches = {arch for r in namespace.repo.trees
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
    if namespace.stable:
        stable_arches = {arch for r in namespace.repo.trees
                         for arch in r.config.stable_arches}
        arches = arches.intersection(stable_arches)

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
            keywords = set()
            stable_keywords = set()
            unstable_keywords = set()
            for pkg in pkgs:
                for x in pkg.keywords:
                    if x[0] == '~':
                        unstable_keywords.add(x[1:])
                    else:
                        stable_keywords.add(x)
            if options.unstable:
                keywords.update(unstable_keywords)
            if options.only_unstable:
                keywords.update(unstable_keywords.difference(stable_keywords))
            if not keywords or options.stable:
                keywords.update(stable_keywords)
            arches = options.arches.intersection(keywords)
            out.write(' '.join(
                sorted(arches.intersection(options.native_arches)) +
                sorted(arches.intersection(options.prefix_arches))))
        else:
            out.write(PkgTable(pkgs, options.arches))


class PkgTable(object):

    def __init__(self, pkgs, arches):
        self.pkgs = pkgs
        self.arches = arches

    def __str__(self):
        s = []
        for pkg in sorted(self.pkgs):
            s.append('{}: {}'.format(pkg.fullver, ' '.join(pkg.keywords)))
        return '\n'.join(s)
