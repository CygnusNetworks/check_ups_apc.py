#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name='check_ups_apc.py',
	version='0.10',
	description='Nagios Check for APC USVs',
	author='Lukas Schauer',
	author_email='l.schauer@cygnusnetworks.de',
	license='GPL',
	packages=['ups_apc_snmp'],
	scripts=['check_ups_apc'],
	install_requires=['configparser', 'nagiosplugin', 'pysnmp'])
