#!/usr/bin/env python
"""
--------
Copyright (c) 2014, Joseph Malone and Brandon Silver (part of a Summer Internship)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of
conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of
conditions and the following disclaimer in the documentation and/or other materials provided
with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS
OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.
--------

This program automates the bulk addition of IP addresses into Juniper SSG and SRX firewall devices.

NOTE: written for Python 2.x, NOT 3.x

New in Version 3:
    1) Commands to SSG devices are now executed in one ssh session instead of many
    2) Commands to SRX devices are now executed in one ssh session instead of many
    3) When adding addresses to a group, there is a limit to the number in a group.
        SSG: See http://kb.juniper.net/InfoCenter/index?page=content&id=KB5296
        SRX: See ???
       You can set this limit in the CLI: -g int. Default is 256 IPs.
    4) When last tested, this version could import 2000 IPs:
        To the SSG in ~4 min (500 per minute; ~8 a second)
        To the SRX in ~40 min (50 per minute; ~1 a second) 
        (The difference is due to how each device handles an IP import. I've tried
        to optimize the process as much as possible. The SRX just takes time.)
"""

from datetime import date
import sys
import argparse
import subprocess
import paramiko
import getpass
import socket
import base64
import time
import math

__version__ = "3.0"
__authors__ = "Brandon Silver and Joseph Malone, Summer Internship 2014"
__date__ = "08/14/2014"

class BatchGroup(object):
    """
    The information common to SSG and SRX systems that is needed to perform a
    batch run. Subclass for specific devices/platforms.
    """
    def __init__(self, add_settings_commands, remove_settings_commands,
            hostname, ssh_user, ssh_pass):
        self.add_settings_commands = add_settings_commands
        self.remove_settings_commands = remove_settings_commands
        self.hostname = hostname
        self.ssh_user = ssh_user
        self.ssh_pass = ssh_pass

    def __str__(self):
        return "\n".join(x for x in (self.add_settings_commands + self.remove_settings_commands))

    def print_add_settings_commands(self):
        """
        Prints out the commands to add the settings to the device.
        """
        for command in self.add_settings_commands:
            print command

    def print_remove_settings_commands(self):
        """
        Prints out the commands to remove the settings from the device.
        """
        for command in self.remove_settings_commands:
            print command

class SSG(BatchGroup):
    """
    An extension of the BatchGroup class with ScreenOS specifics.
    """
    def __init__(self, ip_addrs=None, netmask=None,
            addr_description="", addr_group_prefix=None, zone=None,
            group_limit=None, hostname=None, ssh_user=None, ssh_pass=None):

        # sane defaults for ScreenOS systems
        if netmask is None:
            netmask = "255.255.255.255"
        if addr_group_prefix is None:
            addr_group_prefix = "Deny_addr"
        if addr_description is None:
            addr_description = date.today().isoformat()
        if zone is None:
            zone = "V1-Untrust"
        if group_limit is None:
            group_limit = 256            
        if ssh_user is None:
            ssh_user = "netscreen"

        # check for blank list of IPs. If blank, throw exception.
        if ip_addrs is None:
            raise Exception("ip_addrs cannot be None.")

        self.ip_addrs = ip_addrs
        self.netmask = netmask
        self.addr_description = addr_description
        self.addr_group_prefix = addr_group_prefix
        self.zone = zone
        self.group_limit = group_limit
        self.hostname = hostname
        self.ssh_user = ssh_user
        self.ssh_pass = ssh_pass
        self.set_commands = gen_ssg_set_commands(ip_addrs, addr_group_prefix,
                                addr_description, group_limit, zone, netmask)
        self.get_results_command = 'get config'
        self.unset_commands = gen_ssg_unset_commands(ip_addrs, addr_group_prefix,
                                addr_description, group_limit, zone, netmask)
        BatchGroup.__init__(self, self.set_commands, self.unset_commands,
                self.hostname, self.ssh_user, self.ssh_pass)

    def __str__(self):
        return BatchGroup.__str__(self)

    def run_add_settings_commands(self):
        """
        Runs the commands to add the settings to the device.
        """
        run_via_ssh_ssg(self.set_commands, self.hostname, self.ssh_user, self.ssh_pass)

    def run_remove_settings_commands(self):
        """
        Runs the commands to remove the settings from the device.
        """
        run_via_ssh_ssg(self.unset_commands, self.hostname, self.ssh_user, self.ssh_pass)

def run_via_ssh_ssg(commands, hostname, user, password):
    """
    Runs the command on the device via SSH with username+password
    authentication. WARNING: does NOT verify the authenticity of the device.
    DO NOT USE OVER UNTRUSTED CONNECTIONS!!!
    """ 
    # low-level setup of an SSH connection using the paramiko library
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((hostname, 22))
    tport = paramiko.Transport(sock)
    paramiko.util.log_to_file("paramiko_log.txt")
    tport.start_client()
    channel = tport.open_session()
    channel.set_combine_stderr(True)
    channel.setblocking(blocking=0)
    channel.settimeout(timeout = 0.5)
    tport.auth_password(user, password)
    channel.invoke_shell()
    time.sleep(0.4)

    # instead of doing one command per ssh session, now run through the
    # whole list of commands in one session
    result=""
    #trouble tracks socket.timeouts() and other errors
    trouble=""
    for command in commands:
        # send the command and get the results
        channel.send(command.rstrip()+"\r\n")
        coutstring=""
        result=""
        
        # prints out the prompt from the device, command, and result, if any
        try:
            while not channel.closed:
                coutstring = channel.recv(1024)
                result += coutstring
                if len(coutstring) < 1024:
                    break
            print result
        except:
            trouble += "Had trouble with " + command + ", please check."
    # there's one command result that needs to be retrieved and must be done
    # outside the for loop. And sometimes there's nothing there.
    try:
        final_result = ""
        while not channel.closed:
            coutstring = channel.recv(1024)
            final_result += coutstring
            if len(coutstring) < 1024:
                break
        print final_result.replace(result, "")
    except:
        trouble += "Had trouble with " + command + ", please check."
    print trouble
    # close the connection
    channel.close()
    tport.close()
    sock.close()

def gen_ssg_set_commands(ip_addrs, addr_group_prefix, addr_description, group_limit, zone,
        netmask):
    """
    Returns a list of "set" commands for SSG devices.
    
    NOTE: this is automatically done when instantiating a SSG
    BatchGroup.
    """
    # the list to hold the commands
    commands = []
       
    # formats the "set address" commands
    for ip in ip_addrs:
        ip = ip.rstrip()
        command = ('set address "'+zone+'" "'+ip+'" '+ip+' '+netmask+
                ' "'+addr_description+'"')
        commands.append(command)

    # figure out the necessary number of address groups
    num_of_groups = math.floor((len(ip_addrs)-1)/group_limit)
    count_ips = 1
    
    # formats the "set group address" commands
    # determine group numbers and append to group names
    for ip in ip_addrs:
        ip = ip.rstrip()
        if num_of_groups > 0:
            group_num = int(math.floor((count_ips-1)/group_limit)) + 1
            multiple_groups = "_" + str(group_num)
        else:
            multiple_groups = ""
        command = ('set group address "'+zone+'"'
            ' "'+addr_group_prefix+'_'+addr_description+multiple_groups+'" add "'+ip+'"')
        commands.append(command)
        count_ips += 1
    
    # return the generated commands
    return commands

def gen_ssg_unset_commands(ip_addrs, addr_group_prefix, addr_description, group_limit, zone,
        netmask):
    """
    Returns a list of "unset" commands for SSG devices.

    NOTE: this is automatically done when instantiating a SSG 
    BatchGroup.
    """
    # the list to hold the commands
    commands = []

    # formats the "unset group address" commands
    num_of_groups = math.floor(len(ip_addrs)/group_limit)
    count_ips = 1
    # determine group numbers and append to group names
    for ip in ip_addrs:
        ip = ip.rstrip()
        if num_of_groups > 0:
            group_num = int(math.floor((count_ips-1)/group_limit)) + 1
            multiple_groups = "_" + str(group_num)
        else:
            multiple_groups = ""
        command = ('unset group address "'+zone+'"'
            ' "'+addr_group_prefix+'_'+addr_description+multiple_groups+'" remove "'+ip+'"')
        commands.append(command)
        count_ips += 1

    # add the command to remove the address group object    
    num_of_groups = int(math.floor((len(ip_addrs)-1)/group_limit)) + 1
    # if there's group_limit or fewer ip's, don't append group number
    if num_of_groups == 1:
        commands.append('unset group address'+
        ' "'+zone+'" "'+addr_group_prefix+'_'+addr_description+'"')
    else:
        for group in range(1, num_of_groups+1):
            multiple_groups = "_" + str(group)
            commands.append('unset group address'+
            ' "'+zone+'" "'+addr_group_prefix+'_'+addr_description+multiple_groups+'"')       

    # formats the "unset address" commands
    for ip in ip_addrs:
        command = 'unset address "'+zone+'" "'+ip+'"'
        commands.append(command)

    # return the generated commands
    return commands

class SRX(BatchGroup):
    """
    An extension of the BatchGroup class with SRX specifics.
    """
    def __init__(self, ip_addrs=None, netmask=None,
            addr_description="", addr_group_prefix=None, zone=None,
            group_limit=None, hostname=None, ssh_user=None, ssh_pass=None):

        # sane defaults for SRX systems
        if netmask is None:
            netmask = "255.255.255.255"
        if addr_group_prefix is None:
            addr_group_prefix = "Deny_addr"
        if addr_description is None:
            addr_description = date.today().isoformat()
        if zone is None:
            zone = "V1-Untrust"
        if group_limit is None:
            group_limit = 256 
        if ssh_user is None:
            # Assume we want root access? TODO: figure out default user
            ssh_user = "root"

        self.ip_addrs = ip_addrs
        self.netmask = netmask
        self.addr_description = addr_description
        self.addr_group_prefix = addr_group_prefix
        self.zone = zone
        self.group_limit = group_limit
        self.hostname = hostname
        self.ssh_user = ssh_user
        self.ssh_pass = ssh_pass
        self.set_commands = gen_srx_set_commands(ip_addrs, addr_group_prefix,
                                addr_description, group_limit, zone, netmask)
        self.delete_commands = gen_srx_delete_commands(ip_addrs, addr_group_prefix,
                                addr_description, group_limit, zone, netmask)
        self.get_results_command = 'show configuration | display set'
        BatchGroup.__init__(self, self.set_commands, self.delete_commands,
                self.hostname, self.ssh_user, self.ssh_pass)

    def run_add_settings_commands(self):
        """
        Runs the commands to add the settings to the device.
        """
        commands = ("\nconfigure\n" + "\n".join(x for x in (self.set_commands)) +
                    "\ncommit check\n" + "commit\n" + "exit\n")
        run_via_ssh_srx(self.set_commands, self.hostname, self.ssh_user, self.ssh_pass)

    def run_remove_settings_commands(self):
        """
        Runs the commands to remove the settings from the device.
        """
        commands = ("\nconfigure\n" + "\n".join(x for x in (self.delete_commands)) +
                    "\ncommit check\n" + "commit\n" + "exit\n")
        run_via_ssh_srx(self.delete_commands, self.hostname, self.ssh_user, self.ssh_pass)

def run_via_ssh_srx(commands, hostname, user, password):
    """
    Runs a command on a juniper device using password authentication.
    
    The command argument can consist of multiple commands joined together by
    newlines; in this case, each command is executed in the same shell session.
    """
    #setup connection
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        conn = s.connect(hostname, username=user, password=password, port=22)

        channel = s.invoke_shell()
        channel.settimeout(timeout=0.7)
        channel.set_combine_stderr(True)
        stdin = channel.makefile('wb')
        stdout = channel.makefile('rb')
        #Finish out the list of commands
        commands.insert(0, 'configure') #enter config mode
        commands.insert(1, 'rollback') #clear out any config changes to start clear - roll back to last committed config
        commands.append('commit check') #verify pendign commit
        commands.append('commit') #commit changes
        commands.append('exit') #exit config mode
        #Basic format that the command list should be in:
        #commands = ['configure', 'rollback', 'set security zones security-zone detrust address-book address 1.1.6.10 1.1.6.10/32',
        #            'commit check', 'commit', 'exit']
        for command in commands:
            #Must put a new line at the end of each command
            stdin.write(command.rstrip() + '\n')
            stdin.flush()
            if command == 'commit' or command == 'commit check':
                #Need to wait longer for this to happen so that response can be retrived
                time.sleep(5)
                #channel.recv_ready() #too fast
            elif command == 'configure' or command == 'rollback':
                #Takes some time, but not a ton
                time.sleep(1)
            else:
                time.sleep(.05)
                #print channel.recv_exit_status() #never returns
            #Print out what the SRX machine is running and saying
            try:
                result=""
                while not channel.closed:
                    coutstring = channel.recv(1024)
                    result += coutstring
                    if len(coutstring) < 1024:
                        break
                print result
            except:
                print "Oh, no. I broke! Report a bug. Problem command: " + command
            #This part below here should never actually print.
            #It checks to make sure that nothing is left in the buffer
            trouble=""
            try:
                while not channel.closed:
                    coutstring = channel.recv(1024)
                    trouble += coutstring
                    if len(coutstring) < 1024:
                        break
                print ">>>>>>>"
                print trouble
                print "<<<<<<<"
            except:
                #TODO: Make this part better.
                trouble += "Had trouble with " + command + ", please check."
                #print trouble
        #Sleep just to make sure it can finish commands
        time.sleep(5)
        channel.close()
    except paramiko.AuthenticationException:
        print "Authentication failed."
    s.close()
          
def gen_srx_set_commands(ip_addrs, addr_group_descr, addr_description, group_limit, zone,
        netmask):
    """
    Returns a list of "set" commands for SRX devices.

    TODO: handling of netmasks (i.e., allow ranges of IPs to be
    specified)
    """
    # the list to hold the commands
    commands = []

    # formats the address set commands
    # TODO: should we use "untrust" in place of "V1-Untrust" for the zones?
    # I.e., should we translate from netscreen zones to "srx" zones? Is there
    # even a difference in practice?

    # figure out the necessary number of address groups
    num_of_groups = math.floor((len(ip_addrs)-1)/group_limit)
    count_ips = 1
    # create multiple groups, if necessary, using group_limit
    for ip in ip_addrs:
        ip = ip.rstrip()
        if num_of_groups > 0:
            group_num = int(math.floor((count_ips-1)/group_limit)) + 1
            multiple_groups = "_" + str(group_num)
        else:
            multiple_groups = ""
        address = ('set security zones security-zone '+zone+' address-book'
            ' address '+ip+' '+ip+'/32')
        address_set = ('set security zones security-zone '+zone+' address-book'
            ' address-set '+addr_group_descr+'_'+addr_description+multiple_groups+' address '+ip)
        commands.append(address)
        commands.append(address_set)
        count_ips += 1

    # return the generated commands
    return commands

def gen_srx_delete_commands(ip_addrs, addr_group_descr, addr_description, group_limit, zone,
        netmask):
    """
    Returns a list of "delete" commands for SRX devices.
    """
    # the list to hold the commands
    commands = []

    # formats the "unset" commands - multiple groups
    num_of_groups = math.floor(len(ip_addrs)/group_limit)
    count_ips = 1
    
    # formats the unset commands
    # uses grou_limit as necessary
    for ip in ip_addrs:
        ip = ip.rstrip()
        if num_of_groups > 0:
            group_num = int(math.floor((count_ips-1)/group_limit)) + 1
            multiple_groups = "_" + str(group_num)
        else:
            multiple_groups = ""
        address = ('delete security zones security-zone '+zone+' address-book'
            ' address ' +ip+' '+ip+'/32')
        address_set = ('delete security zones security-zone '+zone+' address-book'
            ' address-set '+addr_group_descr+'_'+addr_description+multiple_groups+' address '+ip)
        commands.append(address_set)
        commands.append(address)
        count_ips += 1
    
    # return the list of commands
    return commands

def main():
    """
    Does a bulk load of IP addresses into a firewall device based off of CLI
    arguments.
    """

    # setup the CLI arguments parser
    parser = argparse.ArgumentParser(description=('Generate and run add/remove commands'
                                                  ' for a list of IP addresses.'))
    parser.add_argument('-d', '--description', help='A description of this batch.')
    parser.add_argument('-a', '--action_description', help=('A description of'
                        ' the action these firewall rules are taking. Default: '
                        ' Deny_addr'), default="Deny_addr",
                        metavar='--action-description')
    parser.add_argument('-p', '--path', help=('A path to a file containing one'
                        ' IP address per line.'), required=True)
    parser.add_argument('-z', '--zone', help=('The origin zone for the firewall'
                        ' rule. Default: "V1-Untrust"'), default="V1-Untrust")
    parser.add_argument('-n', '--netmask', help=('The netmask to be used for'
                        ' the firewall rule. Default: 255.255.255.255'),
                        default="255.255.255.255")
#    parser.add_argument('--results', help=('Display the results of each'
#                        ' command sequence.'))
    parser.add_argument('-t', '--device_type', help=('The device type. The only'
                        ' currently supported types are `ssg` and `srx`. Default:'
                        ' ssg'), default="ssg", metavar='device-type')
    parser.add_argument('-g', '--group_limit', help=('The number of addresses per address'
                        ' group. Default: 256'), default="256", metavar='group-limit')
    parser.add_argument('-u', '--user', help=('The username to use when'
                        ' connecting to the firewall device.')) 
    parser.add_argument('device_address', help=('The address or hostname of the'
                        ' device to run the generated commands on.'),
                        metavar='device-address')
    args = parser.parse_args()

    # get input from standard in by default
    # TODO: since adding user interaction prompts, this is broken.
    # IP addresses must be provided in a text file.
    input = sys.stdin

    # if we are supplied with the name of an input file on the command line,
    # use that for input instead of standard in.
    if args.path:
        input = open(args.path)

    # load the IP addresses from the input
    ip_addresses = []
    for line in input:
        ip_addresses.append(line.rstrip())

    # determine which type of batch we should use
    batch = None
    if args.device_type == "ssg":
        batch = SSG(ip_addrs=ip_addresses, netmask=args.netmask,
                    addr_description=args.description,
                    addr_group_prefix=args.action_description, zone=args.zone,
                    group_limit=int(args.group_limit), hostname=args.device_address,
                    ssh_user=args.user)
    elif args.device_type == "srx":
        batch = SRX(ip_addrs=ip_addresses, netmask=args.netmask,
                    addr_description=args.description,
                    addr_group_prefix=args.action_description, zone=args.zone,
                    group_limit=int(args.group_limit), hostname=args.device_address,
                    ssh_user=args.user)
    else:
        raise Exception("Device type not recognized")

    print """
    ADD SETTINGS COMMANDS
    """
    # print the commands to add the settings to the device
    batch.print_add_settings_commands()

    # prompt the user for final approval before running the commands
    user_input = raw_input("\nRun these set commands on "+args.device_address+" ? (y/N) ")
    if user_input == "y" or user_input == "Y":
        # run the commands
        batch.ssh_pass = getpass.getpass("Enter password for user '"+args.user+"': ")
        print "Running commands to add settings to device..."
        batch.run_add_settings_commands()

#    if args.results:
#        print """
#        CONFIGURATION
#        """
#        run_via_ssh_srx(batch.get_results_command, batch.hostname, batch.ssh_user,
#                batch.ssh_pass)

    print """
    REMOVE SETTINGS COMMANDS
    """

    # print the commands to remove the settings from the device
    batch.print_remove_settings_commands()

    # prompt the user for final approval before running the commands 
    user_input = raw_input("\nRun these unset commands on "+args.device_address+" ? (y/N) ")
    if user_input == "y" or user_input == "Y":
        if batch.ssh_pass is None:
            batch.ssh_pass = getpass.getpass("Enter password for user '"+args.user+"': ")
        print "Running commands to remove settings from device..."
        batch.run_remove_settings_commands()

# launches the main function if the script is being executed directly
if __name__ == '__main__':
    main()
