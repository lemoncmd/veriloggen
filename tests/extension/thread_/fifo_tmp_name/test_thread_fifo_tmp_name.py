from __future__ import absolute_import
from __future__ import print_function

import os
import veriloggen
import thread_fifo_tmp_name


def test(request):
    veriloggen.reset()

    simtype = request.config.getoption('--sim')

    rslt = thread_fifo_tmp_name.run(filename=None, simtype=simtype,
                                    outputfile=os.path.splitext(os.path.basename(__file__))[0] + '.out')

    verify_rslt = [line for line in rslt.splitlines() if line.startswith('# verify:')][0]
    assert(verify_rslt == '# verify: PASSED')