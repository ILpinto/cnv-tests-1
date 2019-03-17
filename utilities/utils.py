import json
import logging
import shlex
import subprocess
import time

from _pytest.mark import ParameterSet
from autologs.autologs import generate_logs

LOGGER = logging.getLogger(__name__)


class TimeoutExpiredError(Exception):
    message = 'Timed Out'

    def __init__(self, *value):
        self.value = value

    def __str__(self):
        return "%s: %s" % (self.message, repr(self.value))


class TimeoutSampler(object):
    """
    Samples the function output.

    This is a generator object that at first yields the output of function
    `func`. After the yield, it either raises instance of `timeout_exc_cls` or
    sleeps `sleep` seconds.

    Yielding the output allows you to handle every value as you wish.

    Feel free to set the instance variables.
    """

    def __init__(self, timeout, sleep, func, *func_args, **func_kwargs):
        self.timeout = timeout
        ''' Timeout in seconds. '''
        self.sleep = sleep
        ''' Sleep interval seconds. '''

        self.func = func
        ''' A function to sample. '''
        self.func_args = func_args
        ''' Args for func. '''
        self.func_kwargs = func_kwargs
        ''' Kwargs for func. '''

        self.start_time = None
        ''' Time of starting the sampling. '''
        self.last_sample_time = None
        ''' Time of last sample. '''

        self.timeout_exc_cls = TimeoutExpiredError
        ''' Class of exception to be raised.  '''
        self.timeout_exc_args = (self.timeout,)
        ''' An args for __init__ of the timeout exception. '''

    def __iter__(self):
        if self.start_time is None:
            self.start_time = time.time()
        while True:
            self.last_sample_time = time.time()
            try:
                yield self.func(*self.func_args, **self.func_kwargs)
            except Exception:
                pass

            if self.timeout < (time.time() - self.start_time):
                raise self.timeout_exc_cls(*self.timeout_exc_args)
            time.sleep(self.sleep)

    def wait_for_func_status(self, result):
        """
        Get function and run it for given time until success or timeout. (using __iter__ function)

        Args:
            result (bool): Expected result from func.

        Examples:
            sample = TimeoutSampler(
                timeout=60, sleep=1, func=some_func, func_arg1="1", func_arg2="2"
                )
                if not sample.waitForFuncStatus(result=True):
                    raise Exception
        """
        try:
            for res in self:
                if result == res:
                    return True

        except self.timeout_exc_cls:
            LOGGER.error("(%s) return incorrect status after timeout", self.func.__name__)
            return False


@generate_logs()
def run_command(command):
    """
    Run command on local machine.

    Args:
        command (str): Command to run.

    Returns:
        tuple: True, out if command succeeded, False, err otherwise.
    """
    p = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if err:
        LOGGER.error("Failed to run {cmd}. error: {err}".format(cmd=command, err=err))
        return False, err

    return True, out.decode("utf-8")


@generate_logs()
def run_command_on_pod(command, pod, container=None):
    """
    Run command on pod.

    Args:
        command (str): Command to run.
        pod (str): Pod name.
        container (str): Container name if pod has more then one.

    Returns:
        tuple: True, out if command succeeded, False, err otherwise.
    """
    container_name = "-c {container}".format(container=container or "") if container else ""
    command = "oc exec -i {pod} {container_name} -- {command}".format(
        pod=pod, container_name=container_name, command=command
    )
    return run_command(command=command)


@generate_logs()
def get_json_from_template(file_, **kwargs):
    """
    Generate JSON from template file_

    Args:
        file_ (str): Template file

    Returns:
        dict: Generated from template file

    Examples:
        get_json_from_vm_template(file_='path/to/file/name', NAME='vm-name-1')
    """
    command = "oc process -f {template}".format(template=file_)
    for k, v in kwargs.items():
        command += " -p {k}={v}".format(k=k, v=v)

    res, out = run_command(command=command)
    return {} if not res else json.loads(out).get('items')[0]


def get_test_parametrize_ids(item, params):
    """
    Get test parametrize IDs from the current parametrize run

    Args:
        item (instance): pytest mark object (<func_name>.parametrize)
        params (list): Test parametrize params

    Returns:
        str: Test Id

    Examples:
        _id = get_test_parametrize_ids(
            self.test_create_networks.parametrize,
            ["param_1", "param_2"]
        )
        testflow.step(_id)
    """
    _id = ""
    param = [i for i in item if i.name == "parametrize"]
    param = param[0] if param else None
    if not param:
        return _id

    param_args = param.args
    if not param_args or len(param_args) < 2:
        return _id

    param_args_values = param_args[1]
    param_ids = param.kwargs.get("ids")
    for i in param_args_values:
        if isinstance(i, list) or isinstance(i, tuple):
            for x in i:
                if not isinstance(x, ParameterSet):
                    continue

                x_values = x.values
                if tuple(params) == x_values:
                    return param_ids[param_args_values.index(x)]
    return _id
