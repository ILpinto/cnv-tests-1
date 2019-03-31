#!/usr/bin/env python
# -*- coding: utf-8 -*-

# API
API_VERSION_ALPHA_3 = 'kubevirt.io/v1alpha3'
API_VERSION_V1 = 'v1'
CNV_API_VERSION = API_VERSION_ALPHA_3

# Resources
VMI = 'VirtualMachineInstance'
VM = 'VirtualMachine'
POD = "Pod"
NODE = 'Node'
NAMESPACE = 'Namespace'
CONFIG_MAP = "ConfigMap"

# VMI / Pod status
RUNNING = 'Running'
PENDING = 'Pending'
SUCCEEDED = 'Succeeded'
FAILED = 'Failed'
UNKNOWN = 'Unknown'
COMPLETED = 'Completed'
CRASH_LOOP_BACKOFF = 'CrashLoopBackOff'
ACTIVE = "Active"
