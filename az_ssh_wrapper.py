#!/usr/bin/env python3

# SPDX-FileCopyrightText: © 2024 David Wales, South Western Sydney Primary Health Network
#
# SPDX-License-Identifier: MIT

import getopt
import os
import shutil
import sys


def usage():
    usage = """
SSH wrapper for az ssh

Usage:

This wrapper emulates OpenSSH, but translates the arguments and
supplies them to az ssh so that it can be used by Ansible as the
ansible_ssh_executable.

It also filters out ControlMaster and ControlPersist options, as these
appear to block for the duration of the specified ControlPersist value
when passed to az ssh. See the following GitHub issue for details:
https://github.com/Azure/azure-cli-extensions/issues/7285

Additional options for Azure Arc:
    --arc                   Use Azure Arc mode
    --subscription VALUE    Azure subscription ID
    --resource-group VALUE  Azure resource group name
    --local-user VALUE      Username to connect as

This wrapper supports all arguments supported by OpenSSH 8.9p1:

    az-ssh [-46AaCfGgKkMNnqsTtVvXxYy] [-B bind_interface]
           [-b bind_address] [-c cipher_spec] [-D [bind_address:]port]
           [-E log_file] [-e escape_char] [-F configfile] [-I pkcs11]
           [-i identity_file] [-J [user@]host[:port]] [-L address]
           [-l login_name] [-m mac_spec] [-O ctl_cmd] [-o option] [-p port]
           [-Q query_option] [-R address] [-S ctl_path] [-W host:port]
           [-w local_tun[:remote_tun]] destination [command [argument ...]]

See the ssh man page for details.

Example:

    az-ssh 1.2.3.4
    az-ssh --arc --subscription "subid" --resource-group "rg" --local-user "admin" server1
"""
    print(usage)


def opt_filter(opt):
    """Filter out options which cause problems for az ssh

    For some reason, setting the Control* options causes az ssh to hang
    for the duration of ControlPersist"""
    return not (opt[0] == "-o" and opt[1].startswith("Control"))


def main():
    options = "46AaCfGgKkMNnqsTtVvXxYyB:b:c:D:E:e:f:I:i:J:L:l:m:O:o:p:Q:R:S:W:w:"
    long_options = ["arc", "subscription=", "resource-group=", "local-user="]

    try:
        opts, args = getopt.getopt(sys.argv[1:], options, long_options)
        destination = args.pop(0)
    except (getopt.GetoptError, IndexError) as err:
        print(f"Error: {err}")
        usage()
        sys.exit(2)

    az_path = shutil.which("az")
    # Work around quoting issue on Windows (still works on Linux)
    az_path = f'"{az_path}"'

    arc_mode = False
    subscription = None
    resource_group = None
    local_user = None
    filtered_opts = []
    
    for o, a in opts:
        if o == "--arc":
            arc_mode = True
        elif o == "--subscription":
            subscription = a
        elif o == "--resource-group":
            resource_group = a
        elif o == "--local-user":
            local_user = a
        else:
            filtered_opts.append((o, a))

    ssh_opts = []
    for opt in filter(opt_filter, filtered_opts):
        # Only keep truthy options. e.g.
        # ('-t', '') --> ('t',)
        # (Yes, this is important.)
        ssh_opts += filter(lambda o: o, opt)

    exec_args = [az_path, "ssh"]
    if arc_mode:
        exec_args.append("arc")
        if subscription:
            exec_args.extend(["--subscription", subscription])
        if resource_group:
            exec_args.extend(["--resource-group", resource_group])
        if local_user:
            exec_args.extend(["--local-user", local_user])
        exec_args.extend(["--name", destination])
    else:
        exec_args.extend(["--name", destination])
        
    if ssh_opts or args:
        exec_args.extend(["--", *ssh_opts, *args])

    os.execvp("az", exec_args)


if __name__ == "__main__":
    main()
