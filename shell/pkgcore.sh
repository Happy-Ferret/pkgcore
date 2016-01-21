# Common library of useful shell functions leveraging pkgcore functionality.
# Source this file from your .bashrc, .zshrc, or similar.
#
# Only bash and zsh are currently supported.

# determine interactive parent shell
PKGSHELL=$(ps -p $$ -ocomm=)
if [[ ${PKGSHELL} != "bash" && ${PKGSHELL} != "zsh" ]]; then
	echo "pkgcore.sh: unsupported shell: ${PKGSHELL}" >&2
	return 1
fi

if [[ ${PKGSHELL} == "bash" ]]; then
	SCRIPTDIR=$(dirname $(realpath ${BASH_SOURCE[0]}))
else
	SCRIPTDIR=$(dirname $(realpath ${(%):-%x}))
fi

source "${SCRIPTDIR}"/${PKGSHELL}/pkgcore.${PKGSHELL}
export PATH=${SCRIPTDIR}/bin:${PATH}
unset PKGSHELL SCRIPTDIR

# interactively choose a value from an array
#
# usage: _choose "${array[@]}"
# returns: index of array choice (assuming array indexing starts at 1)
_choose() {
	local choice x i=1
	for x in $@; do
		echo "  ${i}: ${x}" >&2
		(( i++ ))
	done
	echo -n "Please select one: " >&2
	read choice
	if [[ ${choice} -lt 1 || ${choice} -gt ${#@} ]]; then
		echo "Invalid choice!" >&2
		return 1
	fi
	echo ${choice}
}

# change to a package directory
#
# usage: pcd pkg [repo]
# example: pcd sys-devel/gcc gentoo
#
# This will change the current working directory to the sys-devel/gcc directory
# in the gentoo repo. Note that pkgcore's extended atom syntax is supported so
# one can also abbreviate the command to `pcd gcc gentoo` assuming there is
# only one package with a name of 'gcc' in the gentoo repo. In the case where
# multiple matches are found the list of choices is returned to select from.
#
# This should work for any local repo type on disk, e.g. one can also use this
# to enter the repos for installed or binpkgs via 'vdb' or 'binpkg' repo
# arguments, respectively.
pcd() {
	local pkgpath=$(_pkgattr path "$@")
	[[ -z ${pkgpath} ]] && return 1

	# find the nearest parent directory
	while [[ ! -d ${pkgpath} ]]; do
		pkgpath=$(dirname "${pkgpath}")
	done

	pushd "${pkgpath}" >/dev/null
}
