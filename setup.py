#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name='check_ups_apc.py',
	version='0.13',
	description='Nagios Check for APC USVs',
	author='Lukas Schauer, Dr. Torge Szczepanek',
	author_email='debian@cygnusnetworks.de',
	license='Apache 2.0',
	packages=['ups_apc_snmp'],
	scripts=['check_ups_apc'],
	zip_safe=False,
	install_requires=['configparser', 'nagiosplugin', 'pysnmp'])
