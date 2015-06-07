__author__ = 'Ming'

import subprocess


def shell_command(data): # data is an array
    p = subprocess.Popen(data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out, err