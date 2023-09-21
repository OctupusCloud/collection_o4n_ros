# Ansible Collection - octupus.o4n_ruggedcom_ros

Collection to automate tasks on Ruggedcom ROS devices.

## Modules

- o4n_ros_command: Executes arbitrary commands against a Ruggedcom ROS device. it works with Telnet and SSH protocols.
- o4n_ros_facts (planned): Gather facts on Ruggedcom ROS devices and return as ansible_facts.

## Requirements

- Ansible >= 2.10
- Netmiko >= 2.4.2
