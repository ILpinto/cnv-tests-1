
import logging
from autologs.autologs import generate_logs


import pexpect

LOGGER = logging.getLogger(__name__)


class DistroNotSupported(Exception):
    pass


class Console(object):
    def __init__(self, vm, distro, username=None, password=None, namespace=None):
        """
        Connect to VM console

        Args:
            vm (str): VM name.
            distro (str): Distro name (fedora, cirros, alpine)
            username (str): Username for login.
            password (str): Password for login.
            namespace (str): VM namespace

        Examples:
            with console.Console(vm=vm_name, distro='fedora') as vmc:
                vmc.sendline('some command)
                vmc.expect('some output')
        """
        self.vm = vm
        self.distro = distro
        self.username = username
        self.password = password
        self.namespace = namespace
        try:
            eval("self.{distro}".format(distro=self.distro))
        except AttributeError:
            raise DistroNotSupported("{distro} is not supported".format(distro=self.distro))

        self.err_msg = "Failed to get console to {vm}. error: {error}"
        cmd = "virtctl console {vm}".format(vm=self.vm)
        if namespace:
            cmd += " -n {namespace}".format(namespace=self.namespace)

        self.child = pexpect.spawn(cmd, encoding='utf-8')

    def __enter__(self):
        return eval("self.{distro}".format(distro=self.distro))()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._exit()

    @generate_logs()
    def fedora(self):
        """
        Connect to Fedora

        Returns:
            spawn: Spawn object
        """
        self.child.send("\n\n")
        self.child.expect("login:")
        self.child.sendline(self.username or "fedora")
        self.child.expect("Password:")
        self.child.sendline(self.password or "fedora")
        self.child.expect("$")
        if self.child.after:
            LOGGER.error(self.err_msg.format(vm=self.vm, error=self.child.after))
            return False

        return self.child

    @generate_logs()
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

    @generate_logs()
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

    def _exit(self):
        """
        Exit from Fedora
        """
        self.child.send("exit")
        self.child.send("\n\n")
        self.child.expect("login:")
        self.child.close()
