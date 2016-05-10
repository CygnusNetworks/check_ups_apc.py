<?php

$def[1] = '';
$def[2] = '';
$def[3] = '';
$def[4] = '';

for ($i=1; $i <= count($DS); $i++) {
  switch($NAME[$i]) {
    case 'input_voltage': $def[1] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'output_voltage': $def[1] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'input_frequency': $def[2] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'output_frequency': $def[2] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'battery_voltage': $def[3] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'battery_capacity': $def[3] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    case 'battery_temperature': $def[4] .= rrd::def($NAME[$i], $RRDFILE[1], $DS[$i]); break;
    default: break;
  }
}

$ds_name[1] = 'Voltages';
$opt[1] = "--upper-limit 250 --lower-limit 200 --vertical-label \"V\"  --title $hostname";
$def[1] .= rrd::gradient("input_voltage", "f0f0f0","21db2a", "Input Voltage");
$def[1] .= rrd::gprint("input_voltage", "AVERAGE", "Average %5.1lf V");
$def[1] .= rrd::gprint("input_voltage", "MAX", "Max %5.1lf V");
$def[1] .= rrd::gprint("input_voltage", "LAST", "Last %5.1lf V\\n");

$def[1] .= rrd::gradient("output_voltage", "f0f0f0", "0000b0","Output Voltage");
$def[1] .= rrd::gprint("output_voltage", "AVERAGE", "Average %5lf V");
$def[1] .= rrd::gprint("output_voltage", "MAX", "Max %5lf V");
$def[1] .= rrd::gprint("output_voltage", "LAST", "Last %5lf V\\n");

$ds_name[2] = 'Frequencies';
$opt[2] = "--upper-limit 55 --lower-limit 45 --vertical-label \"Hz\"  --title $hostname";
$def[2] .= rrd::gradient("input_frequency", "f0f0f0","21db2a", "Input Frequency");
$def[2] .= rrd::gprint("input_frequency", "AVERAGE", "Average %5.1lf V");
$def[2] .= rrd::gprint("input_frequency", "MAX", "Max %5.1lf V");
$def[2] .= rrd::gprint("input_frequency", "LAST", "Last %5.1lf V\\n");

$def[2] .= rrd::gradient("output_frequency", "f0f0f0", "0000b0","Output Frequency");
$def[2] .= rrd::gprint("output_frequency", "AVERAGE", "Average %5lf Hz");
$def[2] .= rrd::gprint("output_frequency", "MAX", "Max %5lf Hz");
$def[2] .= rrd::gprint("output_frequency", "LAST", "Last %5lf Hz\\n");

$ds_name[3] = 'Battery Status';
$opt[3] = "--upper-limit 100 --lower-limit 0 --vertical-label \"\"  --title $hostname";
$def[3] .= rrd::gradient("battery_voltage", "f0f0f0", "0000b0","Battery Voltage");
$def[3] .= rrd::gprint("battery_voltage", "AVERAGE", "Average %5lf V");
$def[3] .= rrd::gprint("battery_voltage", "MAX", "Max %5lf V");
$def[3] .= rrd::gprint("battery_voltage", "LAST", "Last %5lf V\\n");

$def[3] .= rrd::gradient("battery_capacity", "f0f0f0", "0000b0","Battery Capacity");
$def[3] .= rrd::gprint("battery_capacity", "AVERAGE", "Average %5lf %%");
$def[3] .= rrd::gprint("battery_capacity", "MAX", "Max %5lf %%");
$def[3] .= rrd::gprint("battery_capacity", "LAST", "Last %5lf %%\\n");

$ds_name[4] = 'Battery Temperature';
$opt[4] = "--upper-limit 60 --lower-limit \"-10\" --vertical-label \"°C\"  --title $hostname";
$def[4] .= rrd::gradient("battery_temperature", "ffff42", "ee7318", "Battery Temperature");
$def[4] .= rrd::gprint("battery_temperature", "AVERAGE", "Average %5.1lf °C");
$def[4] .= rrd::gprint("battery_temperature", "MAX", "Max %5.1lf °C");
$def[4] .= rrd::gprint("battery_temperature", "LAST", "Last %5.1lf °C\\n");
?>
