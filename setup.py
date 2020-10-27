#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name='check_ups_apc.py',
	version='0.14',
	description='Nagios Check for APC USVs',
	author='Lukas Schauer, Dr. Torge Szczepanek',
	author_email='debian@cygnusnetworks.de',
	license='Apache 2.0',
	packages=['ups_apc_snmp'],
	entry_points={'console_scripts': ["check_ups_apc = ups_apc_snmp.nagios_plugin:main"]},
	zip_safe=False,
	install_requires=['configparser', 'nagiosplugin', 'pysnmp'])
