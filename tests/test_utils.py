import logging

from autologs.autologs import generate_logs

from utilities import utils

LOGGER = logging.getLogger(__name__)


@generate_logs()
def wait_for_vm_interfaces(vmi, timeout=600):
    """
    Wait until guest agent report VMI network interfaces.

    Args:
        vmi (VirtualMachineInstance): VMI object.
        timeout (int): Maximum time to wait for interfaces status

    Returns:
        bool: True if agent report VMI interfaces.

    Raises:
        TimeoutExpiredError: After timeout reached.
    """
    sampler = utils.TimeoutSampler(timeout=timeout, sleep=1, func=vmi.get)
    LOGGER.info('Wait until guest agent is active')
    try:
        for sample in sampler:
            #  Check if guest agent is activate
            agent_status = [
                i for i in sample.get('status', {}).get('conditions', {}) if
                i.get('type') == 'AgentConnected' and i.get('status') == 'True'
            ]
            if agent_status:
                LOGGER.info('Wait until VMI report network interfaces status')
                for sample in sampler:
                    #  Get MVI interfaces from guest agent
                    ifcs = sample.get('status', {}).get('interfaces', [])
                    active_ifcs = [
                        i for i in ifcs if i.get('ipAddress') and i.get('interfaceName')
                    ]
                    if len(active_ifcs) == len(ifcs):
                        return True
                LOGGER.error('VMI did not report network interfaces status in given time')

    except utils.TimeoutExpiredError:
        LOGGER.error('Guest agent is not installed or not active')
        raise
