#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import os

import configparser
import nagiosplugin
import nagiosplugin.result
import nagiosplugin.state

import ups_apc_snmp
import ups_apc_snmp.snmpclient

MIB_PATH = os.path.realpath(os.path.dirname(ups_apc_snmp.__file__))

_log = logging.getLogger('nagiosplugin')


class UPSAPCSummary(nagiosplugin.Summary):
	def ok(self, results):  # pylint: disable=R0201
		if 'error_status' in results['reachable'].metric.value:
			summary = 'Device is not reachable through SNMP with error %s' % results['reachable'].metric.value['error_status']
		else:
			try:
				summary = ''
				summary += '%s - ' % (results['unit_type'].metric.value)
				summary += 'BATTERY:(%s, capacity %d%%, temperature %d C, runtime %d minutes) ' % (results['battery_status'].metric.value, results['battery_capacity'].metric.value, results['battery_temperature'].metric.value, results['battery_run_time_remaining'].metric.value / 60.0)
				summary += 'INPUT:(voltage %d V, frequency %d Hz) ' % (results['input_voltage'].metric.value, results['input_frequency'].metric.value)
				summary += 'OUTPUT:(voltage %d V, frequency %d Hz, load %d%%) ' % (results['output_voltage'].metric.value, results['output_frequency'].metric.value, results['output_load'].metric.value)
				summary += 'DIAGNOSTICS:(date %s, result %s) ' % (results['diagnostics_date'].metric.value, results['diagnostics_result'].metric.value)
				if ('uio_temp1' in results and not results['uio_temp1'].metric.value == 'U') and ('uio_temp2' in results and not results['uio_temp2'].metric.value == 'U'):
					summary += 'TEMP:(temp1 %d C, temp2 %d C) ' % (results['uio_temp1'].metric.value, results['uio_temp2'].metric.value)
				elif 'uio_temp1' in results and not results['uio_temp1'].metric.value == 'U':
					summary += 'TEMP:(temp1 %d) ' % results['uio_temp1'].metric.value

				summary += 'LAST EVENT:%s' % (results['input_fail_cause'].metric.value)
			except KeyError as _:
				summary = "No data available"

		return summary

	def problem(self, results):
		return '{0} - {1}'.format(results.first_significant, self.ok(results))


class PerformanceContext(nagiosplugin.Context):  # pylint: disable=too-few-public-methods
	def __init__(self, name, fmt_metric='{name} is {valueunit}', result_cls=nagiosplugin.result.Result):  # pylint: disable=too-many-arguments
		super(PerformanceContext, self).__init__(name, fmt_metric, result_cls)

	def performance(self, metric, resource):  # pylint: disable=W0613,R0201
		return nagiosplugin.performance.Performance(metric.name, metric.value)

	def evaluate(self, metric, resource):  # pylint: disable=W0613
		return self.result_cls(nagiosplugin.state.Ok, None, metric)


class BatteryPackContext(nagiosplugin.Context):  # pylint: disable=too-few-public-methods
	def __init__(self, name, battery_ignore_replacement, fmt_metric=None, result_cls=nagiosplugin.result.Result):  # pylint: disable=too-many-arguments
		super(BatteryPackContext, self).__init__(name, fmt_metric, result_cls)
		self.battery_ignore_replacement = battery_ignore_replacement

	def evaluate(self, metric, resource):  # pylint: disable=W0613
		warnings = []
		crits = []

		for pack in list(metric.value):
			if pack['cartridge_status'][0] == '1':
				crits.append("Battery pack %d cartridge %d disconnected (Serial: %s)" % (pack['index'], pack['cartridge_index'], pack['serial']))
			if pack['cartridge_status'][1] == '1':
				warnings.append("Battery pack %d cartridge %d overvoltage (Serial: %s)" % (pack['index'], pack['cartridge_index'], pack['serial']))
			if pack['cartridge_status'][2] == '1' and self.battery_ignore_replacement is False:
				crits.append("Battery pack %d cartridge %d needs replacement (Serial: %s)" % (pack['index'], pack['cartridge_index'], pack['serial']))
			if pack['cartridge_status'][3] == '1':
				crits.append("Battery pack %d cartridge %d over-temperature (Serial: %s)" % (pack['index'], pack['cartridge_index'], pack['serial']))
			if pack['cartridge_status'][4:].strip('0'):
				warnings.append("Battery pack %d cartridge %d has issues (Serial: %s)" % (pack['index'], pack['cartridge_index'], pack['serial']))
			if pack['cartridge_health'][0] == '0' and pack['cartridge_installdate'] != "01/01/2000" and self.battery_ignore_replacement is False:
				warnings.append("Battery pack %d cartridge %d should be replaced (Serial: %s, Installed: %s, Replace: %s)" % (pack['index'], pack['cartridge_index'], pack['serial'], pack['cartridge_installdate'], pack['cartridge_replacedate']))

		if crits:
			return self.result_cls(nagiosplugin.state.Critical, ", ".join(crits + warnings), metric)
		elif warnings:
			return self.result_cls(nagiosplugin.state.Warn, ", ".join(warnings), metric)
		else:
			return self.result_cls(nagiosplugin.state.Ok, None, metric)


class BoolContext(nagiosplugin.Context):  # pylint: disable=too-few-public-methods
	def __init__(self, name, ok_text=None, crit_text=None, fmt_metric='{name} is {valueunit}', result_cls=nagiosplugin.result.Result):  # pylint: disable=too-many-arguments
		self.ok_text = ok_text
		self.crit_text = crit_text
		super(BoolContext, self).__init__(name, fmt_metric, result_cls)

	def evaluate(self, metric, resource):  # pylint: disable=W0613
		if metric.value:
			return self.result_cls(nagiosplugin.state.Ok, self.ok_text, metric)
		else:
			return self.result_cls(nagiosplugin.state.Critical, self.crit_text, metric)


class BoolContextWarning(BoolContext):  # pylint: disable=too-few-public-methods
	def __init__(self, name, ok_text=None, warn_text=None, fmt_metric='{name} is {valueunit}', result_cls=nagiosplugin.result.Result):  # pylint: disable=too-many-arguments
		self.ok_text = ok_text
		self.warn_text = warn_text
		super(BoolContextWarning, self).__init__(name, fmt_metric, result_cls)

	def evaluate(self, metric, resource):  # pylint: disable=W0613
		if metric.value:
			return self.result_cls(nagiosplugin.state.Ok, self.ok_text, metric)
		else:
			return self.result_cls(nagiosplugin.state.Warn, self.warn_text, metric)


class ElementContext(nagiosplugin.Context):  # pylint: disable=too-few-public-methods
	def __init__(self, name, ok_text=None, warn_text=None, crit_text=None, unknown_text=None, ok_values=None, warn_values=None, crit_values=None, fmt_metric='{name} is {valueunit}', result_cls=nagiosplugin.result.Result):  # pylint: disable=too-many-arguments
		self.ok_text = ok_text
		self.warn_text = warn_text
		self.crit_text = crit_text
		self.unknown_text = unknown_text
		self.ok_values = ok_values or []
		self.warn_values = warn_values or []
		self.crit_values = crit_values or []
		super(ElementContext, self).__init__(name, fmt_metric, result_cls)

	def evaluate(self, metric, resource):  # pylint: disable=W0613
		if metric.value in self.ok_values:
			return self.result_cls(nagiosplugin.state.Ok, self.ok_text, metric)
		elif metric.value in self.warn_values:
			return self.result_cls(nagiosplugin.state.Warn, self.crit_text, metric)
		elif metric.value in self.crit_values:
			return self.result_cls(nagiosplugin.state.Critical, self.crit_text, metric)
		else:
			return self.result_cls(nagiosplugin.state.Unknown, self.unknown_text, metric)


class SNMPContext(nagiosplugin.Context):  # pylint: disable=too-few-public-methods
	def evaluate(self, metric, resource):  # pylint: disable=W0613
		if metric.value["status"]:
			return self.result_cls(nagiosplugin.state.Ok, None, metric)
		else:
			return self.result_cls(nagiosplugin.state.Critical, "Unreachable - %s" % metric.value["error_indication"], metric)


class UPSAPC(nagiosplugin.Resource):  # pylint: disable=too-few-public-methods
	def __init__(self, args):
		self.args = args
		ups_apc_snmp.snmpclient.add_mib_path(MIB_PATH)
		self.snmpclient = None

	def probe(self):  # pylint: disable=too-many-locals
		_log.debug("Probing APC UPS device %s through SNMP", self.args.host)
		self.snmpclient = ups_apc_snmp.snmpclient.SnmpClient(self.args.host, ups_apc_snmp.snmpclient.snmp_auth_data_v2c(community=self.args.community), timeout=self.args.snmp_timeout, retries=self.args.retries)

		if not self.snmpclient.alive:
			_log.warn("Device is not reachable through SNMP with error %s", self.snmpclient.error_status)
			yield nagiosplugin.Metric('reachable', dict(status=self.snmpclient.alive, error_indication=self.snmpclient.error_indication, error_status=self.snmpclient.error_status, error_varbinds=self.snmpclient.error_varbinds))
			return

		_log.debug("Queried APC UPS device %s through SNMP - device is reachable", self.args.host)
		yield nagiosplugin.Metric('reachable', dict(status=True))
		_log.debug("Found Sysname %s and sysdescr %s", self.snmpclient.sysname, self.snmpclient.sysdescr)

		if not str(self.snmpclient.sysdescr).startswith("APC"):
			raise nagiosplugin.CheckError("Device is not a APC UPS device - System description is %s", self.snmpclient.sysdescr)

		_log.debug("Starting SNMP polling of host %s", self.args.host)

		sysuptime = self.snmpclient.get("SNMPv2-MIB::sysUpTime.0")

		yield nagiosplugin.Metric("sysuptime", int(sysuptime.get_value() / 100 / 60))

		# device
		unit_type = self.snmpclient.get("PowerNet-MIB::upsBasicIdentModel.0").get_value()
		_log.debug("Device %s unit type is %s", self.args.host, unit_type)
		yield nagiosplugin.Metric('unit_type', unit_type)

		diagnostics_date = self.snmpclient.get("PowerNet-MIB::upsAdvTestLastDiagnosticsDate.0").get_value()
		_log.debug("Device %s last diagnostics date was %s", self.args.host, diagnostics_date)
		yield nagiosplugin.Metric('diagnostics_date', diagnostics_date)

		diagnostics_result = self.snmpclient.get("PowerNet-MIB::upsAdvTestDiagnosticsResults.0").get_named_value()
		_log.debug("Device %s last diagnostics result was %s", self.args.host, diagnostics_result)
		yield nagiosplugin.Metric('diagnostics_result', diagnostics_result)

		uio_temp1 = self.snmpclient.get("PowerNet-MIB::uioSensorStatusTemperatureDegC.1.1").get_value()
		try:
			uio_temp1 = int(uio_temp1)
			_log.debug("Device %s external temperature sensor 1 is at %dC", self.args.host, uio_temp1)
			yield nagiosplugin.Metric('uio_temp1', uio_temp1)
		except:  # pylint: disable=W0702
			yield nagiosplugin.Metric('uio_temp1', 'U')

		uio_temp2 = self.snmpclient.get("PowerNet-MIB::uioSensorStatusTemperatureDegC.1.2").get_value()
		try:
			uio_temp2 = int(uio_temp2)
			_log.debug("Device %s external temperature sensor 2 is at %dC", self.args.host, uio_temp2)
			yield nagiosplugin.Metric('uio_temp2', uio_temp2)
		except:  # pylint: disable=W0702
			yield nagiosplugin.Metric('uio_temp2', 'U')

		# battery
		battery_status = self.snmpclient.get("PowerNet-MIB::upsBasicBatteryStatus.0").get_named_value()
		_log.debug("Device %s battery status is %s", self.args.host, battery_status)
		yield nagiosplugin.Metric('battery_status', battery_status)

		battery_capacity = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecBatteryCapacity.0").get_value()) / 10.0
		_log.debug("Device %s battery capacity is %.1f%%", self.args.host, battery_capacity)
		yield nagiosplugin.Metric('battery_capacity', battery_capacity)

		battery_voltage = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecBatteryActualVoltage.0").get_value()) / 10.0
		_log.debug("Device %s battery voltage is %.1fV", self.args.host, battery_voltage)
		yield nagiosplugin.Metric('battery_voltage', battery_voltage)

		battery_temperature = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecBatteryTemperature.0").get_value()) / 10.0
		_log.debug("Device %s battery temperature is %.1fC", self.args.host, battery_temperature)
		yield nagiosplugin.Metric('battery_temperature', battery_temperature)

		battery_replace_indicator = self.snmpclient.get("PowerNet-MIB::upsAdvBatteryReplaceIndicator.0").get_value() == 2
		_log.debug("Device %s battery replace indicator is %s", self.args.host, 'on' if battery_replace_indicator else 'off')
		yield nagiosplugin.Metric('battery_replace_indicator', not battery_replace_indicator)

		battery_run_time_remaining = self.snmpclient.get("PowerNet-MIB::upsAdvBatteryRunTimeRemaining.0").get_value() / 100
		_log.debug("Device %s battery run time remaining: %ds", self.args.host, battery_run_time_remaining)
		yield nagiosplugin.Metric('battery_run_time_remaining', battery_run_time_remaining)

		batterypacks = []
		batterypacktable_varbinds = self.snmpclient.gettable("PowerNet-MIB::upsHighPrecBatteryPackTable")
		batterypacktable = batterypacktable_varbinds.get_json_name()
		batterypack_serial_prefix = 'PowerNet-MIB::upsHighPrecBatteryPackSerialNumber.'
		batterypackids = list(x[len(batterypack_serial_prefix):] for x in batterypacktable.keys() if x.startswith(batterypack_serial_prefix))
		for batterypackid in batterypackids:
			batterypack = {}
			batterypack['index'] = int(batterypacktable["PowerNet-MIB::upsHighPrecBatteryPackIndex.%s" % batterypackid])
			batterypack['serial'] = batterypacktable["PowerNet-MIB::upsHighPrecBatteryPackSerialNumber.%s" % batterypackid].strip()

			if batterypack['serial']:
				batterypack['status'] = batterypacktable["PowerNet-MIB::upsHighPrecBatteryPackStatus.%s" % batterypackid]
				batterypack['temperature'] = float(batterypacktable["PowerNet-MIB::upsHighPrecBatteryPackTemperature.%s" % batterypackid]) / 10.0

				batterypack['cartridge_index'] = int(batterypacktable["PowerNet-MIB::upsHighPrecBatteryCartridgeIndex.%s" % batterypackid])
				batterypack['cartridge_status'] = batterypacktable["PowerNet-MIB::upsHighPrecBatteryPackCartridgeStatus.%s" % batterypackid]
				batterypack['cartridge_health'] = batterypacktable["PowerNet-MIB::upsHighPrecBatteryPackCartridgeHealth.%s" % batterypackid]
				batterypack['cartridge_installdate'] = batterypacktable["PowerNet-MIB::upsHighPrecBatteryPackCartridgeInstallDate.%s" % batterypackid]
				batterypack['cartridge_replacedate'] = batterypacktable["PowerNet-MIB::upsHighPrecBatteryPackCartridgeReplaceDate.%s" % batterypackid]

				batterypacks.append(batterypack)
				_log.debug("Battery pack: %r", batterypack)

		yield nagiosplugin.Metric('battery_packs', batterypacks)

		# input
		input_voltage = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecInputLineVoltage.0").get_value()) / 10.0
		_log.debug("Device %s input voltage is %.1fV", self.args.host, input_voltage)
		yield nagiosplugin.Metric('input_voltage', input_voltage)

		input_min_voltage = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecInputMinLineVoltage.0").get_value()) / 10.0
		_log.debug("Device %s minimum input voltage is %.1fV", self.args.host, input_min_voltage)
		yield nagiosplugin.Metric('input_min_voltage', input_min_voltage)

		input_max_voltage = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecInputMaxLineVoltage.0").get_value()) / 10.0
		_log.debug("Device %s maximum input voltage is %.1fV", self.args.host, input_max_voltage)
		yield nagiosplugin.Metric('input_max_voltage', input_max_voltage)

		input_frequency = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecInputFrequency.0").get_value()) / 10.0
		_log.debug("Device %s input frequency is %.1fHz", self.args.host, input_frequency)
		yield nagiosplugin.Metric('input_frequency', input_frequency)

		input_fail_cause = self.snmpclient.get("PowerNet-MIB::upsAdvInputLineFailCause.0").get_named_value()
		_log.debug("Device %s input last fail cause is %s", self.args.host, input_fail_cause)
		yield nagiosplugin.Metric('input_fail_cause', input_fail_cause)

		# output
		output_status = self.snmpclient.get("PowerNet-MIB::upsBasicOutputStatus.0").get_named_value()
		_log.debug("Device %s output status is %s", self.args.host, output_status)
		yield nagiosplugin.Metric('output_status', output_status)

		output_voltage = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecOutputVoltage.0").get_value()) / 10.0
		_log.debug("Device %s output voltage is %.1fV", self.args.host, output_voltage)
		yield nagiosplugin.Metric('output_voltage', output_voltage)

		output_current = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecOutputCurrent.0").get_value()) / 10.0
		_log.debug("Device %s output current is %.1fA", self.args.host, output_current)
		yield nagiosplugin.Metric('output_current', output_current)

		output_load = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecOutputLoad.0").get_value()) / 10.0
		_log.debug("Device %s output load is %.1f%%", self.args.host, output_load)
		yield nagiosplugin.Metric('output_load', output_load)

		output_frequency = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecOutputFrequency.0").get_value()) / 10.0
		_log.debug("Device %s output frequency is %.1fHz", self.args.host, output_frequency)
		yield nagiosplugin.Metric('output_frequency', output_frequency)

		output_efficiency = float(self.snmpclient.get("PowerNet-MIB::upsHighPrecOutputEfficiency.0").get_value()) / 10.0
		_log.debug("Device %s output efficiency is %.1f%%", self.args.host, output_efficiency)
		yield nagiosplugin.Metric('output_efficiency', output_efficiency)


@nagiosplugin.guarded
def main():
	argp = argparse.ArgumentParser()
	argp.add_argument('-v', '--verbose', action='count', default=0)
	argp.add_argument('-c', '--config', help='config file', default='/etc/check_ups_apc.conf')
	argp.add_argument('-C', '--community', help='SNMP Community', default='public')
	argp.add_argument('-H', '--host', help='Hostname or network address to check', required=True)
	argp.add_argument('-t', '--timeout', help='Check timeout', type=int, default=30)
	argp.add_argument('-s', '--snmp-timeout', help='SNMP timeout', dest='snmp_timeout', type=int, default=2)
	argp.add_argument('-r', '--retries', help='SNMP retries', type=int, default=3)
	argp.add_argument('-u', '--uptime', help='Uptime limit in minutes to create warning', type=int, default=120)
	argp.add_argument('-b', '--battery-ignore-replacement', help='Ignore battery replacement warnings', action='store_true')
	args = argp.parse_args()

	device_defaults = dict(
		input_voltage_min_warn=215, input_voltage_max_warn=240, input_voltage_min_crit=210, input_voltage_max_crit=245,
		input_frequency_min_warn=48, input_frequency_max_warn=52, input_frequency_min_crit=47, input_frequency_max_crit=53,

		output_voltage_min_warn=215, output_voltage_max_warn=240, output_voltage_min_crit=210, output_voltage_max_crit=245,
		output_frequency_min_warn=48, output_frequency_max_warn=52, output_frequency_min_crit=47, output_frequency_max_crit=53,

		battery_capacity_min_warn=70, battery_capacity_min_crit=50,
		battery_temperature_min_warn=15, battery_temperature_max_warn=30, battery_temperature_min_crit=10, battery_temperature_max_crit=40,

		output_load_max_warn=70, output_load_max_crit=85,
	)
	config_defaults = {'general': {}, args.host: device_defaults}

	config_parser = configparser.ConfigParser(config_defaults)
	config_parser.read(args.config)

	if args.host not in config_parser.sections():
		config_parser.add_section(args.host)

	for key, value in device_defaults.items():
		if not config_parser.has_option(args.host, key):
			config_parser.set(args.host, key, str(value))

	check = nagiosplugin.Check(UPSAPC(args))
	check.add(SNMPContext('reachable'))
	check.add(nagiosplugin.Context('unit_type'))
	check.add(BoolContext('battery_replace_indicator', ok_text="Battery OK", crit_text="Battery needs replacement"))
	check.add(PerformanceContext('diagnostics_date'))
	check.add(ElementContext('diagnostics_result', ok_values=['ok', 'testInProgress'], crit_values=['failed', 'invalidTest']))
	check.add(PerformanceContext('uio_temp1'))
	check.add(PerformanceContext('uio_temp2'))

	# input
	check.add(nagiosplugin.ScalarContext('input_voltage',
											warning='%i:%i' % (config_parser.getint(args.host, 'input_voltage_min_warn'), config_parser.getint(args.host, 'input_voltage_max_warn')),
											critical='%i:%i' % (config_parser.getint(args.host, 'input_voltage_min_crit'), config_parser.getint(args.host, 'input_voltage_max_crit'))))

	check.add(PerformanceContext('input_min_voltage'))
	check.add(PerformanceContext('input_max_voltage'))

	check.add(nagiosplugin.ScalarContext('input_frequency',
											warning='%i:%i' % (config_parser.getint(args.host, 'input_frequency_min_warn'), config_parser.getint(args.host, 'input_frequency_max_warn')),
											critical='%i:%i' % (config_parser.getint(args.host, 'input_frequency_min_crit'), config_parser.getint(args.host, 'input_frequency_max_crit'))))

	check.add(nagiosplugin.Context('input_fail_cause'))

	# output
	check.add(nagiosplugin.ScalarContext('output_voltage',
											warning='%i:%i' % (config_parser.getint(args.host, 'output_voltage_min_warn'), config_parser.getint(args.host, 'output_voltage_max_warn')),
											critical='%i:%i' % (config_parser.getint(args.host, 'output_voltage_min_crit'), config_parser.getint(args.host, 'output_voltage_max_crit'))))

	check.add(nagiosplugin.ScalarContext('output_load',
											warning='0:%i' % (config_parser.getint(args.host, 'output_load_max_warn')),
											critical='0:%i' % (config_parser.getint(args.host, 'output_load_max_crit'))))

	check.add(nagiosplugin.ScalarContext('output_frequency',
											warning='%i:%i' % (config_parser.getint(args.host, 'output_frequency_min_warn'), config_parser.getint(args.host, 'output_frequency_max_warn')),
											critical='%i:%i' % (config_parser.getint(args.host, 'output_frequency_min_crit'), config_parser.getint(args.host, 'output_frequency_max_crit'))))

	output_status_ok_values = [
		'onLine',
		'hotStandby',
	]
	output_status_warn_values = [
		'onBattery',
		'onSmartBoost',  # under-voltage boost
		'softwareBypass',
		'switchedBypass',
		'rebooting',
		'onSmartTrim',  # over-voltage trim
		'ecoMode',  # bypass
		'staticBypassStandby',
	]
	output_status_crit_values = [
		'timedSleeping',  # output off (planned)
		'sleepingUntilPowerReturn',
		'hardwareFailureBypass',
		'emergencyStaticBypass',
		'off',
		'powerSavingMode',  # auto-off
	]
	check.add(ElementContext('output_status', ok_values=output_status_ok_values, warn_values=output_status_warn_values, crit_values=output_status_crit_values))

	check.add(PerformanceContext('output_current'))
	check.add(PerformanceContext('output_efficiency'))

	# battery
	check.add(ElementContext('battery_status', ok_values=['batteryNormal'], warn_values=['batteryLow'], crit_values=['batteryInFaultCondition']))

	check.add(nagiosplugin.ScalarContext('battery_capacity',
											warning='%i:100' % (config_parser.getint(args.host, 'battery_capacity_min_warn')),
											critical='%i:100' % (config_parser.getint(args.host, 'battery_capacity_min_crit'))))

	check.add(PerformanceContext('battery_run_time_remaining'))

	check.add(nagiosplugin.ScalarContext('battery_temperature',
											warning='%i:%i' % (config_parser.getint(args.host, 'battery_temperature_min_warn'), config_parser.getint(args.host, 'battery_temperature_max_warn')),
											critical='%i:%i' % (config_parser.getint(args.host, 'battery_temperature_min_crit'), config_parser.getint(args.host, 'battery_temperature_max_crit'))))

	check.add(PerformanceContext('battery_voltage'))

	check.add(BatteryPackContext('battery_packs', args.battery_ignore_replacement))

	check.add(nagiosplugin.ScalarContext('sysuptime', warning='@%i:%i' % (0, args.uptime)))

	check.add(UPSAPCSummary())

	check.main(args.verbose, timeout=args.timeout)

if __name__ == "__main__":
	main()
