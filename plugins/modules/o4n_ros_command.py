#!/usr/bin/python
from __future__ import (absolute_import, division, print_function)  # Ansible
__metaclass__ = type

DOCUMENTATION = r'''
---
module: o4n_ros_command

short_description: Ansible module for executing commands in Ruggedcom ROS devices

version_added: "1.0.3"

description: Ansible module for executing commands in Ruggedcom ROS devices.

options:
    host:
        description: Hostname or IP address of the Ruggedcom ROS device to connect to.
        required: true
        type: str
    protocol:
        description: Protocol to be used
        choices: ['ssh', 'telnet']
        default: ssh
        required: false
        type: str
    port:
        description: TCP port to use . (default 22)
        required: false
        type: int
        default: 22
    user:
        description: User to login into the device
        required: true
        type: str
    password:
        description: Password to login into the device
        required: true
        type: str
    commands:
        description: List of commands to execute on the Ruggedcom OS device.
        required: true
        type: list
    telnet_timeout:
        description: Number of seconds to wait for answers from the device.
        required: false
        type: int
        default: 10

requirements:
    - netmiko
    - telnetlib
    - Establecer `ansible_python_interpreter` a Python 3 si es necesario.

author:
    - Marcos Schonfeld (@marcosmas28)
'''

EXAMPLES = r'''
# Execute the module with all options
- name: Running show product info
  o4n_ros_command:
    host: "{{ ansible_host }}"
    protocol: "{{ ansible_protocol }}"
    port: "{{ ansible_port }}"
    user: "{{ ansible_user }}"
    password: "{{ ansible_password }}"
    commands:
      - sql select Serial Number , Main Version from productinfo
      - sql select MAC Address , Order Code , Hardware ID from productinfo
  register: output
'''

RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
content:
    description: the commands output as a string.
    type: str
    returned: always
    sample: "\
        Serial Number                   Main Version                                    \
        RUME924058381                   v4.1.0 (May 09 2014 16:39)                      \
        n1 records selected\
        \u001b[0m\u001b[2K\
        MAC Address       Order Code                                                Hardware ID                   \
        94-B8-C5-F9-75-80 RS900-HI-D-L2-L2-00                                       RS900 (v2, 40-00-0066)        \
        n1 records selected"
'''

# Python Modules
from ansible.module_utils.basic import AnsibleModule
from netmiko import ConnectHandler, NetmikoTimeoutException
import telnetlib
import time
import logging


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(required=True, type='str'),
            protocol=dict(required=False, type='str', choices=["ssh", "telnet"], default="ssh"),
            port=dict(required=False, type='int', default=22),
            user=dict(required=True, type='str'),
            password=dict(required=True, type='str', no_log=True),
            commands=dict(required=True, type='list'),
            telnet_timeout=dict(required=False, type='int', default=10),
        )
    )

    host = module.params.get("host")
    protocol = module.params.get("protocol")
    port = module.params.get("port")
    user = module.params.get("user")
    password = module.params.get("password")
    commands = module.params.get("commands")
    telnet_timeout = module.params.get("telnet_timeout")

    module_success = False

    # Prevent Paramiko logs
    logger = logging.getLogger("paramiko")
    logger.addHandler(logging.NullHandler())

    if protocol == "telnet":
        try:
            tn_client = telnetlib.Telnet(host=host, port=port, timeout=telnet_timeout)
        except Exception as err:
            ret_msg = 'O4N_ERROR: Telnet Connection Exception (a)\nConnection settings: ' + user + '@' + host + ':' + str(port) + '\n' + str(err)
            module.fail_json(msg=ret_msg, failed=True, changed=False)
            return()
        # send user
        try:
            tn_client.read_until(b'Enter User Name: ', telnet_timeout)
        except Exception as err:
            ret_msg = 'O4N_ERROR: Telnet Connection Exception (b)\nConnection settings: ' + user + '@' + host + ':' + str(port) + '\n' + str(err)
            module.fail_json(msg=ret_msg, failed=True, changed=False)
            return()
        tn_client.write(user.encode() + b'\n')
        # send password
        try:
            tn_client.read_until(b'Password: ', telnet_timeout)
        except Exception as err:
            ret_msg = 'O4N_ERROR: Telnet Connection Exception (c)\nConnection settings: ' + user + '@' + host + ':' + str(port) + '\n' + str(err)
            module.fail_json(msg=ret_msg, failed=True, changed=False)
            return()
        tn_client.write(password.encode() + b'\n')
        # Enter CLI prompt
        tn_client.write(b'\x13')
        tn_client.write(b'cls' + b'\n')
        time.sleep(1)
        try:
            tn_client.read_very_eager()
        except Exception as err:
            ret_msg = 'O4N_ERROR: Telnet Connection Exception (d)\nConnection settings: ' + user + '@' + host + ':' + str(port) + '\n' + str(err)
            module.fail_json(msg=ret_msg, failed=True, changed=False)
            return()
        tn_client.write(b'\n')

        # Check Authentication
        prompt = tn_client.read_until(b'>    ', telnet_timeout)
        if 'Enter User Name:' in prompt.decode('ascii'):
            ret_msg = """
'O4N_ERROR: Telnet Authentication Exception.\n
Authentication to device failed.\n
Common causes of this problem are:\n
1. Invalid username and password\n
2. Connecting to the wrong device\n
Connection settings:
"""
            module.fail_json(msg=ret_msg + user + '@' + host + ':' + str(port), failed=True, changed=False)
            return()

        for command in commands:
            time.sleep(0.2)
            tn_client.write(command.encode() + b'\n')

        # send finish keyword and read output
        tn_client.write(b'    '+b'\n')
        try:
            output = tn_client.read_until(b'>    ', telnet_timeout)
        except Exception as err:
            ret_msg = 'O4N_ERROR: Telnet Command Exception \n' + str(err)
            module.fail_json(msg=ret_msg, failed=True, changed=False)
            return()
        output = output.decode('ascii')
        # close session
        tn_client.close()

        module_success = True
        # Module return
        if module_success:
            module.exit_json(failed=False, content=output)
        else:
            module.fail_json(msg='O4N_ERROR: Module Failed\n', failed=True, changed=False)

    else:
        try:
            ssh_client = ConnectHandler(host, device_type='autodetect', username=user, port=port, password=password, auth_timeout=90, timeout=60)
        except Exception as err:
            ret_msg = 'O4N_ERROR: SSH Connection Exception\n' + str(err)
            module.fail_json(msg=ret_msg, failed=True, changed=False)
            return()
        try:
            ssh_client.send_command_timing('\n \x13', last_read=1)
        except Exception as err:
            ret_msg = 'O4N_ERROR: CLI Prompt Exception\n' + str(err)
            module.fail_json(msg=ret_msg, failed=True, changed=False)
            return()
        output = ""
        for command in commands:
            # Aux Vars:
            more_prompt = "--More-- or (q)uit"
            cmd_output = '>' + command + '\n'
            # Execute command:
            try:
                page = ssh_client.send_command_timing(command, last_read=1)
            except Exception as err:
                ret_msg = 'O4N_ERROR: Send Command Exception\n' + str(err)
                module.fail_json(msg=ret_msg, failed=True, changed=False)
                return()
            while True:
                try:
                    cmd_output += page
                    if more_prompt in page:
                        try:
                            page = ssh_client.send_command_timing('\n', last_read=1)
                        except Exception as err:
                            ret_msg = 'O4N_ERROR: Pagination Exception\n' + str(err)
                            module.fail_json(msg=ret_msg, failed=True, changed=False)
                            return()
                    else:
                        break
                except NetmikoTimeoutException:
                    print("Time Out Exeption")
                    break
            output += cmd_output.replace(more_prompt, "")

        ssh_client.disconnect()

        # Module return
        module_success = True
        if module_success:
            module.exit_json(failed=False, content=output)
        else:
            module.fail_json(msg='O4N_ERROR: Module Failed\n', failed=True, changed=False)


if __name__ == "__main__":
    main()
