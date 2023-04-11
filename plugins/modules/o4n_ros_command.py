#!/usr/bin/python3
from __future__ import (absolute_import, division, print_function) # Ansible
__metaclass__ = type

DOCUMENTATION = r'''
---
module: o4n_ros_command

short_description: Ansible module for executing commands in Ruggedcom ROS devices

version_added: "1.0.0"

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

requirements:
    - netmiko
    - telnetlib

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
    sample: "\nSerial Number                   Main Version                                    \nRUME924058381                   v4.1.0 (May 09 2014 16:39)                      \n\n1 records selected\n\n\u001b[0m\u001b[2K\nMAC Address       Order Code                                                Hardware ID                   \n94-B8-C5-F9-75-80 RS900-HI-D-L2-L2-00                                       RS900 (v2, 40-00-0066)        \n\n1 records selected\n"
'''

# Python Modules
from ansible.module_utils.basic import AnsibleModule
from netmiko import ConnectHandler, NetmikoTimeoutException
import telnetlib
import time

def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(required=True, type='str'),
            protocol=dict(required=False,type='str', choices=["ssh", "telnet"], default="ssh"),
            port=dict(required=False,type='int', default=22),
            user=dict(required=True, type='str'),
            password=dict(required=True, type='str', no_log=True),
            commands=dict(required=True, type='list'),
        )
    )

    host = module.params.get("host")
    protocol = module.params.get("protocol")
    port = module.params.get("port")
    user = module.params.get("user")
    password = module.params.get("password")
    commands = module.params.get("commands")

    module_success = False

    if protocol == "telnet":
        tn_client = telnetlib.Telnet(host=host, port=port)
        # send user
        tn_client.read_until(b'Enter User Name: ')
        tn_client.write(user.encode() + b'\n')
        # send password
        tn_client.read_until(b'Password: ')
        tn_client.write(password.encode() + b'\n')
        # Enter CLI prompt
        #tn_client.read_until(b'X-Logout')
        tn_client.write(b'\x13')

        for command in commands:
            time.sleep(1)
            tn_client.write(command.encode() + b'\n')

        # send finish keyword and read output
        tn_client.write(b'FIN')
        output = tn_client.read_until(b'>FIN')
        output = output.decode('ascii')
        # close session
        tn_client.write(b'logout\n')
        tn_client.close()

        module_success=True
        # Module return
        if module_success:
            module.exit_json(failed=False, content=output)
        else:
            module.exit_json(failed=True, content=output)

    else:
        ssh_client = ConnectHandler(host, device_type='autodetect', username=user, port=port, password=password, auth_timeout=90, timeout=60)
        ssh_client.send_command_timing('\n \x13',last_read=1)
        output=""
        for command in commands:
            # Aux Vars:
            more_prompt = "--More-- or (q)uit"
            cmd_output = ""
            # Execute command:
            page = ssh_client.send_command_timing(command,last_read=1)
            while True:
                try:
                    cmd_output += page
                    if more_prompt in page:
                        page = ssh_client.send_command_timing('\n',last_read=1)
                    else:
                        break
                except NetmikoTimeoutException:
                    print("Time Out Exeption")
                    break
            output += cmd_output.replace(more_prompt,"")

        ssh_client.disconnect()

        # Module return
        module_success=True
        if module_success:
            module.exit_json(failed=False, content=output)
        else:
            module.exit_json(failed=True, content=output)

if __name__ == "__main__":
    main()

