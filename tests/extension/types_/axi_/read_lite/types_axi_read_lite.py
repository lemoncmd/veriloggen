from __future__ import absolute_import
from __future__ import print_function
import sys
import os

# the next line can be removed after installation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))))

from veriloggen import *
import veriloggen.types.axi as axi


def mkMain():
    m = Module('main')
    clk = m.Input('CLK')
    rst = m.Input('RST')

    myaxi = axi.AxiLiteMaster(m, 'myaxi', clk, rst)
    myaxi.disable_write()

    fsm = FSM(m, 'fsm', clk, rst)

    # read address (1)
    araddr1 = 1024
    ack = myaxi.read_request(araddr1, cond=fsm)
    fsm.If(ack).goto_next()

    # read data (1)
    data, valid = myaxi.read_data(cond=fsm)
    sum = m.Reg('sum', 32, initval=0)

    fsm.If(valid)(
        sum.add(data)
    )
    fsm.If(valid).goto_next()

    # read address (2)
    araddr2 = 1024 + 1024
    ack = myaxi.read_request(araddr2, cond=fsm)
    fsm.If(ack).goto_next()

    # read data (2)
    data, valid = myaxi.read_data(cond=fsm)

    fsm.If(valid)(
        sum.add(data)
    )
    fsm.If(valid).goto_next()

    # verify
    expected_sum = araddr1 // 4 + araddr2 // 4
    fsm(
        Systask('display', 'sum=%d expected_sum=%d', sum, expected_sum)
    )
    fsm.If(sum == expected_sum)(
        Systask('display', '# verify: PASSED')
    ).Else(
        Systask('display', '# verify: FAILED')
    )
    fsm.goto_next()

    return m


def mkTest(memimg_name=None):
    m = Module('test')

    # target instance
    main = mkMain()

    # copy paras and ports
    params = m.copy_params(main)
    ports = m.copy_sim_ports(main)

    clk = ports['CLK']
    rst = ports['RST']

    # awready (no stall)
    awready = ports['myaxi_awready']
    _awready = m.TmpWireLike(awready)
    _awready.assign(1)
    m.Always()(awready(_awready))

    # wready (no stall)
    wready = ports['myaxi_wready']
    _wready = m.TmpWireLike(wready)
    _wready.assign(1)
    m.Always()(wready(_wready))

    # bvalid (no stall)
    bvalid = ports['myaxi_bvalid']
    _bvalid = m.TmpWireLike(bvalid)
    _bvalid.assign(0)
    m.Always()(bvalid(_bvalid))

    # arready, rvalid, rdata
    raddr_fsm = FSM(m, 'raddr', clk, rst)
    raddr_fsm(
        ports['myaxi_arready'](0),
        ports['myaxi_rdata'](-1),
        ports['myaxi_rvalid'](0),
    )
    raddr_fsm.If(ports['myaxi_arvalid']).goto_next()

    raddr_fsm.If(ports['myaxi_arvalid'])(
        ports['myaxi_arready'](1),
        ports['myaxi_rdata']((ports['myaxi_araddr'] >> 2) - 1)
    )
    raddr_fsm.goto_next()

    raddr_fsm(
        ports['myaxi_arready'](0),
    )
    raddr_fsm.goto_next()

    raddr_fsm(
        ports['myaxi_rdata'].inc(),
        ports['myaxi_rvalid'](1),
    )
    raddr_fsm.goto_next()

    raddr_fsm.If(ports['myaxi_rready'])(
        ports['myaxi_rvalid'](0)
    )
    raddr_fsm.If(ports['myaxi_rready']).goto_next()

    raddr_fsm.goto_next()

    raddr_fsm.goto_init()

    raddr_fsm.make_always()

    uut = m.Instance(main, 'uut',
                     params=m.connect_params(main),
                     ports=m.connect_ports(main))

    # vcd_name = os.path.splitext(os.path.basename(__file__))[0] + '.vcd'
    # simulation.setup_waveform(m, uut, m.get_vars(), dumpfile=vcd_name)
    simulation.setup_clock(m, clk, hperiod=5)
    init = simulation.setup_reset(m, rst, m.make_reset(), period=100)

    init.add(
        Delay(1000 * 100),
        Systask('finish'),
    )

    return m


def run(filename='tmp.v', simtype='iverilog', outputfile=None):

    if outputfile is None:
        outputfile = os.path.splitext(os.path.basename(__file__))[0] + '.out'

    # memimg_name = 'memimg_' + outputfile

    # test = mkTest(memimg_name=memimg_name)
    test = mkTest()

    if filename is not None:
        test.to_verilog(filename)

    sim = simulation.Simulator(test, sim=simtype)
    rslt = sim.run(outputfile=outputfile)

    return rslt


if __name__ == '__main__':
    rslt = run(filename='tmp.v')
    print(rslt)
