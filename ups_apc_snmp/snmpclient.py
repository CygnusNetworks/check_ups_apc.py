#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import os
import random
import time

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi import builder, view, error
from pysnmp.proto import rfc1902, rfc1905

from pyasn1.type import univ

# Snmp version constants
V1 = 0
V2 = V2C = 1

# The internal mib builder
__mibBuilder = builder.MibBuilder()
__mibViewController = view.MibViewController(__mibBuilder)


def add_mib_path(path):
	"""Add a directory to the MIB search path"""
	if path not in __mibBuilder.getMibPath() and os.path.isdir(path):
		__mibBuilder.setMibPath(*(__mibBuilder.getMibPath() + (path, )))  # pylint: disable=W0142


def load_mibs(*modules):
	"""Load one or more mibs"""
	for m in modules:
		try:
			__mibBuilder.loadModules(m)
		except error.SmiError as e:
			if 'already exported' in str(e):
				continue
			raise


def snmp_auth_data(community, version=V2C, snmp_id=None):
	if snmp_id is None:
		sha_256 = hashlib.sha256()  # pylint: disable=E1101
		sha_256.update(community)
		sha_256.update(str(time.time() * 1000))
		sha_256.update(str(random.random()))
		snmp_id = sha_256.hexdigest()[:32]
	return cmdgen.CommunityData(snmp_id, community, version)


def snmp_auth_data_v1(community, version=V1, snmp_id=None):
	return snmp_auth_data(community, version, snmp_id)


def snmp_auth_data_v2c(community, version=V2C, snmp_id=None):
	return snmp_auth_data(community, version, snmp_id)


class SnmpError(Exception):
	def __init__(self, msg, error_indication, error_status, error_index, varbinds):  # pylint: disable=R0913
		self.msg = msg
		self.error_indication = error_indication
		self.error_status = error_status
		self.error_index = error_index
		self.varbinds = varbinds
		Exception.__init__(self, msg)

	def __str__(self):
		return "%s - with error indication %s and error status %s" % (self.msg, str(self.error_indication), str(self.error_status))


def nodeinfo(oid):
	"""Translate dotted-decimal oid to a tuple with symbolic info"""
	if isinstance(oid, str):
		oid = rfc1902.ObjectName(oid)
	return __mibViewController.getNodeLocation(oid), __mibViewController.getNodeName(oid)


def nodeinfos(*oids):
	return [nodeinfo(oid) for oid in oids]


def nodename(oid):
	"""Translate dotted-decimal oid or oid tuple to symbolic name"""
	if isinstance(oid, str):
		oid = rfc1902.ObjectName(oid)
	oid = __mibViewController.getNodeLocation(oid)
	name = '::'.join(oid[:-1])
	noid = '.'.join([str(x) for x in oid[-1]])
	if noid:
		name += '.' + noid
	return name


def nodenames(*oids):
	return [nodename(oid) for oid in oids]


def nodeid(oid):
	"""Translate named oid to dotted-decimal format"""
	if isinstance(oid, tuple):
		return oid
	elif isinstance(oid, rfc1902.ObjectName):
		return oid
	elif isinstance(oid, str):
		ids = oid.split('.')
		try:
			ids_num = [int(x) for x in ids]
		except ValueError:
			symbols = ids[0].split('::')
			ids = tuple([int(x) for x in ids[1:]])
			mibnode, = __mibBuilder.importSymbols(*symbols)  # pylint: disable=W0142
			oid = mibnode.getName() + ids
			return oid
		else:
			return tuple(ids_num)

	else:
		raise AssertionError("Unknown oid format for %r encountered" % oid)


def nodeids(oids):
	oids_list = []
	for oid in oids:
		oids_list.append(nodeid(oid), )
	oids_list.sort()
	return tuple(set(oids_list))


class SnmpClient(object):  # pylint: disable=R0902
	"""Easy access to an snmp deamon on a host"""

	def __init__(self, host, auth, port=161, timeout=2, retries=3):  # pylint: disable=R0913
		"""Set up the client and detect the community to use"""
		self.host = host
		self.port = port
		self.alive = False
		self.sysname = None
		self.sysdescr = None
		self.auth = auth
		self.timeout = timeout
		self.retries = retries
		self.error_indication = self.error_status = self.error_index = self.error_varbinds = None

		(error_indication, error_status, error_index, varbinds) = cmdgen.CommandGenerator().getCmd(auth, cmdgen.UdpTransportTarget((self.host, self.port), timeout=timeout, retries=retries),
																								nodeid('SNMPv2-MIB::sysName.0'),
																								nodeid('SNMPv2-MIB::sysDescr.0'))
		if error_indication or error_status:
			self.__set_error(error_indication, error_status, error_index, varbinds)
		else:
			assert len(varbinds) == 2
			self.sysname = varbinds[0][1]
			self.sysdescr = varbinds[1][1]
			self.alive = True

	def __set_error(self, error_indication, error_status, error_index, varbinds):
		self.error_indication = error_indication
		self.error_status = error_status
		self.error_index = error_index
		self.error_varbinds = varbinds

	def set_auth_data(self, community, version=V2C, community_index=None):
		self.auth = cmdgen.CommunityData(community_index, community, version)

	def get(self, *oids):
		"""Get a specific node in the tree"""
		assert self.alive is True
		# print "oids is", oids
		oids_trans = nodeids(oids)
		# print "oids_trans are", oids_trans
		(error_indication, error_status, error_index, varbinds) = cmdgen.CommandGenerator().getCmd(self.auth, cmdgen.UdpTransportTarget((self.host, self.port), timeout=self.timeout, retries=self.retries), *oids_trans)  # pylint: disable=W0142
		if error_indication or error_status:
			self.__set_error(error_indication, error_status, error_index, varbinds)
			raise SnmpError("SNMP get command on %s of oid %r failed" % (self.host, oids), error_indication, error_status, error_index, varbinds)
		return SnmpVarBinds(varbinds)

	def gettable(self, *oids):
		"""Get a complete subtable"""
		assert self.alive is True
		oids_trans = nodeids(oids)
		(error_indication, error_status, error_index, varbinds) = cmdgen.CommandGenerator().nextCmd(self.auth, cmdgen.UdpTransportTarget((self.host, self.port), timeout=self.timeout, retries=self.retries), *oids_trans)  # pylint: disable=W0142
		if error_indication or error_status:
			self.__set_error(error_indication, error_status, error_index, varbinds)
			raise SnmpError("SNMP getnext on %s of oid %r failed" % (self.host, oids), error_indication, error_status, error_index, varbinds)
		return SnmpVarBinds(varbinds)

	def set(self, *oidvalues):
		assert self.alive is True
		oidvalues_trans = []
		for oid, value in oidvalues:
			if isinstance(oid, tuple):
				has_str = False
				for entry in oid:
					if isinstance(entry, str):
						has_str = True
						break
				if has_str:  # if oid is a tuple containing strings, assume translation using cmdgen.MibVariable.
					# value must then be a Python type
					assert isinstance(value, int) or isinstance(value, str) or isinstance(value, bool)
					oidvalues_trans.append((cmdgen.MibVariable(*oid), value))  # pylint:disable=W0142
				else:
					# value must be a rfc1902/pyasn1 type
					if not oid[-1] == 0:
						assert isinstance(value, univ.Integer) or isinstance(value, univ.OctetString) or isinstance(value, univ.ObjectIdentifier)
					oidvalues_trans.append((oid, value))
			elif isinstance(oid, str):  # if oid is a string, assume nodeid lookup
				# value must then be a rfc1902/pyasn1 type, if oid is not a scalar
				if not oid.endswith(".0"):
					assert isinstance(value, univ.Integer) or isinstance(value, univ.OctetString) or isinstance(value, univ.ObjectIdentifier)
				oidvalues_trans.append((nodeid(oid), value))

		(error_indication, error_status, error_index, varbinds) = \
			cmdgen.CommandGenerator().setCmd(self.auth, cmdgen.UdpTransportTarget((self.host, self.port), timeout=self.timeout, retries=self.retries), *oidvalues_trans)  # pylint: disable=W0612,W0142
		if error_indication or error_status:
			self.__set_error(error_indication, error_status, error_index, varbinds)
			raise SnmpError("SNMP set command on %s of oid values %r failed" % (self.host, oidvalues_trans), error_indication, error_status, error_index, varbinds)
		return SnmpVarBinds(varbinds)

	def matchtables(self, index, *tables):
		"""Match a list of tables using either a specific index table or the
		common tail of the OIDs in the tables"""
		assert self.alive is True
		oid_to_index = {}
		result = {}
		indexlen = 1
		if index:
			#  Use the index if available
			varbinds = self.gettable(index)
			for entry in varbinds.get_varbinds():
				oid, index = entry[0]
				oid_to_index[oid[-indexlen:]] = index
				result[index] = []
		else:
			# Generate an index from the first table
			baselen = len(nodeid(tables[0]))
			varbinds = self.gettable(tables[0])
			for oid, value in varbinds.get_varbinds():
				indexlen = len(oid) - baselen
				oid_to_index[oid[-indexlen:]] = oid[-indexlen:]
				result[oid[-indexlen:]] = [value]
			tables = tables[1:]
		# Fetch the tables and match indices
		res = self.gettable(*tables)
		for entry in res.get_varbinds():
			for oid, value in entry:
				index = oid_to_index[oid[-indexlen:]]
				result[index].append(value)
		return result


class SnmpVarBinds(object):
	def __init__(self, varbinds):
		self.__varbinds = varbinds
		self.__varbinds_dict = None

	def __str__(self):
		text = str(self.get_json_name())
		return text

	def __repr__(self):
		text = repr(self.get_json_name())
		return text

	def dictify(self):
		if self.__varbinds_dict is None:
			self.__varbinds_dict = {}
			for entry in self.__varbinds:
				if isinstance(entry, list):
					for oid, value in entry:
						# always store internal data using rfc1902.ObjectNames, which are pyasn1 ObjectIdentifiers, which behave like tuples
						if not value.isSameTypeWith(rfc1905.noSuchObject):
							self.__varbinds_dict[rfc1902.ObjectName(oid)] = value
				else:
					oid, value = entry
					if not value.isSameTypeWith(rfc1905.noSuchObject):
						self.__varbinds_dict[rfc1902.ObjectName(oid)] = value

	def get_by_dict(self, oid):
		self.dictify()
		if oid is None and len(self.__varbinds_dict.keys()) == 1:
			oid = self.__varbinds_dict.keys()[0]
		elif oid is None:
			raise RuntimeError("Cannot query oid %r if multiple varBinds keys are present")
		if isinstance(oid, str):
			if self.__varbinds_dict.has_key(oid):
				value = self.__varbinds_dict[oid]
			else:
				value = self.__varbinds_dict[rfc1902.ObjectName(nodeid(oid))]
			if value.isSameTypeWith(rfc1905.noSuchObject):
				return None
			return value
		elif isinstance(oid, tuple) or isinstance(oid, rfc1902.ObjectName):
			value = self.__varbinds_dict[oid]
			if value.isSameTypeWith(rfc1905.noSuchObject):
				return None
			else:
				return value
		else:
			raise RuntimeError("Unknown format of oid %r with type %s" % (oid, oid.__class__.__name__))

	def get_value(self, oid=None):
		return self.get_by_dict(oid)

	def get_varbinds(self):
		return self.__varbinds

	def get_dict(self):
		self.dictify()
		return self.__varbinds_dict

	def __get_json(self, keytype=str):
		json = {}
		for key, value in self.get_dict().items():
			if isinstance(value, univ.OctetString):
				value = str(value)
			elif isinstance(value, univ.Integer):
				value = int(value)
			elif isinstance(value, univ.ObjectIdentifier):
				value = str(value)
			else:
				raise AssertionError("Unknown type %s encountered for oid %s" % (value.__class__.__name__, key))
			json[keytype(key)] = value
		return json

	def get_json_oid(self):
		return self.__get_json()

	def get_json_name(self):
		return self.__get_json(keytype=nodename)
