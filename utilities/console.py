import sys

import pexpect
import logging

LOGGER = logging.getLogger(__name__)


class Console(object):
    def __init__(self, vm, username=None, password=None, namespace=None):
        """
        Connect to VM console

        Args:
            vm (str): VM name.
            username (str): Username for login.
            password (str): Password for login.
            namespace (str): VM namespace
        """
        self.vm = vm
        self.username = username
        self.password = password
        self.namespace = namespace
        self.err_msg = "Failed to get console to {vm}. error: {error}"
        cmd = "virtctl console {vm}".format(vm=self.vm)
        if namespace:
            cmd += "-n {namespace}".format(namespace=self.namespace)

        self.child = pexpect.spawn(cmd, encoding='utf-8')

    def fedora(self):
        """
        Connect to Fedora

        Returns:
            spawn: Spawn object
        """
        self.child.send("\n\n")
        self.child.expect("login: ")
        self.child.sendline(self.username or "fedora")
        self.child.expect("Password: ")
        self.child.sendline(self.password or "fedora")
        self.child.expect("$")
        if self.child.after:
            LOGGER.error(self.err_msg.format(vm=self.vm, error=self.child.after))
            return False

        return self.child

    def cirros(self):
        """
        Connect to Cirros

        Returns:
            spawn: Spawn object
        """
        self.child.send("\n\n")
        self.child.expect("login as 'cirros' user. default password: 'gocubsgo'. use 'sudo' for root.")
        self.child.send("\n")
        self.child.expect("login:")
        self.child.sendline(self.username or "cirros")
        self.child.expect("Password:")
        self.child.sendline(self.password or "gocubsgo")
        self.child.expect("\\$")
        if self.child.after:
            LOGGER.error(self.err_msg.format(vm=self.vm, error=self.child.after))
            return False

        return self.child

    def alpine(self):
        """
        Connect to Alpine

        Returns:
            spawn: Spawn object
        """
        self.child.send("\n\n")
        self.child.expect("localhost login:")
        self.child.sendline(self.username or "root")
        self.child.expect("localhost:~#")
        if self.child.after:
            LOGGER.error(self.err_msg.format(vm=self.vm, error=self.child.after))
            return False

        return self.child
