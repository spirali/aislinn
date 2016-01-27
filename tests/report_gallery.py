import utils

utils.REPORT_GALLERY = True
import os

if os.path.isdir(utils.AISLINN_REPORT_GALLERY):
    for item in os.listdir(utils.AISLINN_REPORT_GALLERY):
        path = os.path.join(utils.AISLINN_REPORT_GALLERY, item)
        if os.path.isfile(path):
            os.unlink(path)
else:
    os.makedirs(utils.AISLINN_REPORT_GALLERY)


from test_base import *  # noqa
from test_sendrecv import *  # noqa
from test_mem import *  # noqa
from test_collective import *  # noqa
from test_comm import *  # noqa
from test_misc import *  # noqa

import unittest

if __name__ == "__main__":
    unittest.main()
