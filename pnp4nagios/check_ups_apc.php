<?php

$def[1] = '';
$def[2] = '';
$def[3] = '';
$def[4] = '';

for ($i=1; $i <= count($DS); $i++) {
  switch($NAME[$i]) {
    case 'input_voltage': $def[1] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'input_frequency': $def[1] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'output_voltage': $def[2] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'output_frequency': $def[2] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'battery_voltage': $def[3] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'battery_capacity': $def[3] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'battery_temperature': $def[4] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'uio_temp1': $def[4] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'uio_temp2': $def[4] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    default: break;
  }
}

$ds_name[1] = 'Input';
$opt[1] = "--upper-limit 250 --lower-limit 40 --vertical-label \"V / Hz\"  --title $hostname";
$def[1] .= rrd::line1("input_voltage", "#21db2a", "Input Voltage");
$def[1] .= rrd::gprint("input_voltage", "AVERAGE", "Average %5.1lf V");
$def[1] .= rrd::gprint("input_voltage", "MAX", "Max %5.1lf V");
$def[1] .= rrd::gprint("input_voltage", "LAST", "Last %5.1lf V\\n");

$def[1] .= rrd::line1("input_frequency", "#0000b0", "Input Frequency");
$def[1] .= rrd::gprint("input_frequency", "AVERAGE", "Average %5.1lf Hz");
$def[1] .= rrd::gprint("input_frequency", "MAX", "Max %5.1lf Hz");
$def[1] .= rrd::gprint("input_frequency", "LAST", "Last %5.1lf Hz\\n");

$ds_name[2] = 'Output';
$opt[2] = "--upper-limit 55 --lower-limit 40 --vertical-label \"V / Hz\"  --title $hostname";
$def[2] .= rrd::line1("output_voltage", "#21db2a", "Output Voltage");
$def[2] .= rrd::gprint("output_voltage", "AVERAGE", "Average %5.1lf V");
$def[2] .= rrd::gprint("output_voltage", "MAX", "Max %5.1lf V");
$def[2] .= rrd::gprint("output_voltage", "LAST", "Last %5.1lf V\\n");

$def[2] .= rrd::line1("output_frequency", "#0000b0","Output Frequency");
$def[2] .= rrd::gprint("output_frequency", "AVERAGE", "Average %5.1lf Hz");
$def[2] .= rrd::gprint("output_frequency", "MAX", "Max %5.1lf Hz");
$def[2] .= rrd::gprint("output_frequency", "LAST", "Last %5.1lf Hz\\n");

$ds_name[3] = 'Battery Status';
$opt[3] = "--upper-limit 100 --lower-limit 0 --vertical-label \"\"  --title $hostname";
$def[3] .= rrd::line1("battery_voltage", "#21db2a", "Battery Voltage");
$def[3] .= rrd::gprint("battery_voltage", "AVERAGE", "Average %5.1lf V");
$def[3] .= rrd::gprint("battery_voltage", "MAX", "Max %5.1lf V");
$def[3] .= rrd::gprint("battery_voltage", "LAST", "Last %5.1lf V\\n");

$def[3] .= rrd::line1("battery_capacity", "#e000ff", "Battery Capacity");
$def[3] .= rrd::gprint("battery_capacity", "AVERAGE", "Average %5.1lf %%");
$def[3] .= rrd::gprint("battery_capacity", "MAX", "Max %5.1lf %%");
$def[3] .= rrd::gprint("battery_capacity", "LAST", "Last %5.1lf %%\\n");

$ds_name[4] = 'Temperature';
$opt[4] = "--upper-limit 50 --lower-limit 0 --vertical-label \"C\"  --title $hostname";
$def[4] .= rrd::line1("battery_temperature", "#ff0000", "Battery Temperature");
$def[4] .= rrd::gprint("battery_temperature", "AVERAGE", "Average %5.1lf °C");
$def[4] .= rrd::gprint("battery_temperature", "MAX", "Max %5.1lf °C");
$def[4] .= rrd::gprint("battery_temperature", "LAST", "Last %5.1lf °C\\n");

$def[4] .= rrd::line1("uio_temp1", "#00ff00", "External Sensor 1");
$def[4] .= rrd::gprint("uio_temp1", "AVERAGE", "Average %5.1lf °C");
$def[4] .= rrd::gprint("uio_temp1", "MAX", "Max %5.1lf °C");
$def[4] .= rrd::gprint("uio_temp1", "LAST", "Last %5.1lf °C\\n");

$def[4] .= rrd::line1("uio_temp2", "#0000ff", "External Sensor 2");
$def[4] .= rrd::gprint("uio_temp2", "AVERAGE", "Average %5.1lf °C");
$def[4] .= rrd::gprint("uio_temp2", "MAX", "Max %5.1lf °C");
$def[4] .= rrd::gprint("uio_temp2", "LAST", "Last %5.1lf °C\\n");

?>
