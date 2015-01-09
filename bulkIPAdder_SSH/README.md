bulkIPAdder_SSH
=========
This Python script automates the bulk addition of IP addresses into Juniper SSG and SRX firewall devices.

New in Version 3:

    1) Commands to SSG devices are now executed in one SSH session instead of many
    2) Commands to SRX devices are executed in one SSH session and the resulting output is displayed
    3) When adding addresses to a group, there is a limit to the number in a group.
        SSG: See http://kb.juniper.net/InfoCenter/index?page=content&id=KB5296
        SRX: See ???
       You can set this limit in the CLI: -g int. Default is 256 IPs.
    4) When last tested, this version could import 2000 IPs:
        To the SSG in ~4 min (500 per minute; ~8 a second)
        To the SRX in ~40 min (50 per minute; ~1 a second)
        (The difference is due to how each device handles an IP import. The process has been optimized 
        as much as possible, the SRX just takes time.)

A caveat with this script: you cannot provide IP addresses via standard in; they must be placed in a text file 
and a path to that text file must be provided as one of the script’s CLI arguments.

Required modules:

1. datetime (included with python >= 2.3)
2. sys (included in all python versions AFAIK)
3. subprocess (included with python >= 2.4) (not actually used in the script at the moment)
4. paramiko (NOT included by default, install with e.g., `sudo pip install paramiko`, requires python >= 2.6)
5. getpass (included with python >= 2.4)
6. socket (included with all python versions AFAIK)
7. base64 (included with python >= 2.4)
8. time (included with python >= 2.2)

Help/documentation:
```python
usage: bulk_add_automated_v2.py [-h] [-d DESCRIPTION]
                                [-a --action-description] -p PATH [-z ZONE]
                                [-n NETMASK] [-t device-type] [-u USER]
                                device-address

Generate and run add/remove commands for a list of IP addresses.
positional arguments:

  device-address        The address or hostname of the device to run the
                        generated commands on.

optional arguments:

  -h, --help            show this help message and exit
  -d DESCRIPTION, --description DESCRIPTION
                        A description of this batch.
  -a --action-description, --action_description --action-description
                        A description of the action these firewall rules are
                        taking. Default: Deny_addr
  -p PATH, --path PATH  A path to a file containing one IP address per line.
  -z ZONE, --zone ZONE  The origin zone for the firewall rule. Default:
                        "V1-Untrust"
  -n NETMASK, --netmask NETMASK
                        The netmask to be used for the firewall rule. Default:
                        255.255.255.255
  -t device-type, --device_type device-type
                        The device type. The only currently supported types
                        are `ssg` and `srx`. Default: ssg
  -u USER, --user USER  The username to use when connecting to the firewall
                        device.
```
