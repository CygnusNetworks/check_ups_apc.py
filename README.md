## APC UPS Nagios Check

This Nagios/Icinga Check provides the ability to query APC UPS devices (aka PowerNet) for current status.

It will output voltages, frequencies, battery state and more values for tools like pnp4nagios.  
Implementation is in Python. You will need Python libraries pnp4nagios and pysnmp as dependencies.

You need to enable the SNMP Agent on your APC device and set a SNMP Read community.

### Installation (manual using pip) on your Nagios Host
```
pip install nagiosplugin pysnmp
python setup.py install
ln -s /usr/bin/check_ups_apc /usr/lib/nagios/plugins/check_ups_apc
```

### Installation Debian package

For Debian you can use the provided Debian package. Debian Jessie should be fine without any additional packages. For Debian Wheezy you will need python-configparser from Backports.

### Usage example

Nagios Plugin called manually:i

```
./check_ups_apc -H 1.2.3.4 -C public
```

See check_ups_apc -h for additional command line arguments. Use -vvv to get Debug Output including additional system information.

### Using a config file

You can use a config file to change ranges of the warning and critical value ranges for the different monitored devices. The config is expected to be named /etc/check_ups_apc.conf.
Use the command line Switch --config (-c) to override this behaviour.

The config file must contain sections named after the specified hostname/hostaddress of the device (parameter -H) of the check_ups_apc call. You can list the changed parameters within this section. Non present value will take over the defaults. Example (all values are the default values):

/etc/check_ups_apc.conf
```
[10.0.0.1]
input_voltage_min_warn = 215
input_voltage_min_crit = 210
input_voltage_max_warn = 240
input_voltage_max_crit = 245

input_frequency_min_warn = 48
input_frequency_min_crit = 47
input_frequency_max_warn = 52
input_frequency_max_crit = 53

output_voltage_min_warn = 215
output_voltage_min_crit = 210
output_voltage_max_warn = 240
output_voltage_max_crit = 245

output_frequency_min_warn = 48
output_frequency_min_crit = 47
output_frequency_max_warn = 52
output_frequency_max_crit = 53

battery_capacity_min_warn = 70
battery_capacity_min_crit = 50

battery_temperature_min_warn = 15
battery_temperature_min_crit = 10
battery_temperature_max_warn = 30
battery_temperature_max_crit = 40
```

### Nagios Integration

Define the commands for Nagios checks and include it in the service definitions:

```
define command {
	command_name	check_ups_apc
	command_line	/usr/lib/nagios/plugins/check_ups_apc -C $ARG1$ -H $HOSTADDRESS$
}
define service {
	use			generic-service-perfdata
	hostgroup_name		ups_apc
	service_description	check_ups_apc
	check_command		check_ups_apc!SNMP_COMMUNITY
}
```
