# Copyright: 2006 Brian Harring <ferringb@gmail.com>
# License: GPL2
# $Id:$

"""
triggers, callables to bind to a step in a MergeEngine to affect changes
"""

__all__ = ["trigger", "SimpleTrigger", "merge_trigger", "unmerge_trigger", "ldconfig_trigger"]

from pkgcore.merge import errors
from pkgcore.util.demandload import demandload
demandload(globals(), """os 
	pkgcore.plugins:get_plugin 
	pkgcore.spawn:spawn""")
import pkgcore.os_data

class trigger(object):

	"""base trigger class"""
	
	def __init__(self, cset_name, ftrigger, register_func=None):

		"""
		@param cset_name: the cset label required for this trigger
		@param ftrigger: actually func to execute when MergeEngine hands control over
		@param register_func: either None, or a callable to execute for handling registering with a MergeEngine instance
		"""
		
		if not isinstance(cset_name, basestring):
			for x in cset_name:
				if not isinstance(x, basestring):
					raise TypeError("cset_name must be either a list, or a list of strings: %s" % x)
		else:
			cset_name = [cset_name]
		self.required_csets = cset_name
		if not callable(ftrigger):
			raise TypeError("ftrigger must be a callable")
		self.trigger = ftrigger
		if register_func is not None:
			if not callable(register_func):
				raise TypeError("register_func must be a callable")
		self.register_func = register_func

	# this should probably be implemented as an associated int that can be used to
	# sort the triggers
	def register(self, hook_name, existing_triggers):
		"""
		register with a MergeEngine
		"""
		if self.register_func is not None:
			self.register_func(self, hook_name, existing_triggers)
		else:
			existing_triggers.append(self)

	def __call__(self, engine, csets):
		"""execute the trigger"""
		self.trigger(engine, csets)

	def __str__(self):
		return "trigger: %s for csets(%s)" % (self.trigger, self.required_csets)


class SimpleTrigger(trigger):

	"""simplified trigger class; for most triggers, this is what you want to use"""
	
	def __init__(self, cset_name, ftrigger, register_func=None):
		"""
		@param cset_name: cset to use
		@param ftrigger: callable to execute when 'triggered'
		@param register_func: None, or callable to call to register with a MergeEngine
		"""
		if not isinstance(cset_name, basestring):
			raise TypeError("cset_name must be a string")
		trigger.__init__(self, [cset_name], ftrigger, register_func=register_func)

	def __call__(self, engine, csets):
		self.trigger(engine, csets[self.required_csets[0]])


def run_ldconfig(engine, cset, ld_so_conf_file="etc/ld.so.conf"):
	"""execute ldconfig updates"""

	# this sucks. not very fine grained, plus it can false positive on binaries
	# libtool fex, which isn't a lib
	fireit = False
	for x in cset.iterfiles():
		s = x.location
		if s[-3:] == ".so":
			pass
		elif os.path.basename(s[:3]).lower() != "lib":
			pass
		else:
			continue
		fireit = True
		break

	if fireit:
		if engine.offset is None:
			offset = '/'
		else:
			offset = engine.offset
		basedir = os.path.join(offset, os.path.dirname(ld_so_conf_file))
		if not os.path.exists(basedir):
			os.mkdir(os.path.join(offset, basedir))
		f = os.path.join(offset, ld_so_conf_file)
		if not os.path.exists(f):
			open(f, "w")
		ret = spawn(["/sbin/ldconfig", "-r", offset], fd_pipes={1:1, 2:2})
		if ret != 0:
			raise errors.TriggerWarning("ldconfig returned %i from execution" % ret)


def merge_trigger(cset="install"):
	"""generate a trigger for the actual copy to the livefs"""
	return SimpleTrigger(cset,
		lambda engine, cset: get_plugin("fs_ops", "merge_contents")(cset))

def unmerge_trigger(cset="uninstall"):
	"""generate a trigger for the actual unmerge from the livefs"""
	return SimpleTrigger(cset, lambda e, c: get_plugin("fs_ops", "unmerge_contents")(c))

def ldconfig_trigger(cset="modifying"):
	"""generate a trigger to execute any ldconfig calls required"""
	return SimpleTrigger(cset, run_ldconfig)

def fix_default_gid(gid=pkgcore.os_data.portage_gid, replacement=pkgcore.os_data.root_gid, cset="new_cset"):
	def change_gid(engine, cset):
		# do it as a list, since we're mutating the set
		resets = [x.change_attributes(gid=replacement) for x in cset if x.gid == gid]
		cset.update(resets)
	return SimpleTrigger(cset, change_gid)

def fix_default_uid(uid=pkgcore.os_data.portage_uid, replacement=pkgcore.os_data.root_uid, cset="new_cset"):
	def change_uid(engine, cset):
		# do it as a list, since we're mutating the set
		resets = [x.change_attributes(uid=replacement) for x in cset if x.uid == uid]
		cset.update(resets)
	return SimpleTrigger(cset, change_uid)
