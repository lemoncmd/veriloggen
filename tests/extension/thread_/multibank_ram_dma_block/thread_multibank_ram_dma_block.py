from __future__ import absolute_import
from __future__ import print_function
import sys
import os

# the next line can be removed after installation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from veriloggen import *
import veriloggen.thread as vthread
import veriloggen.types.axi as axi


def mkLed(memory_datawidth=128):
    m = Module('blinkled')
    clk = m.Input('CLK')
    rst = m.Input('RST')

    datawidth = 32
    addrwidth = 10
    numbanks = 4
    myaxi = vthread.AXIM(m, 'myaxi', clk, rst, memory_datawidth)
    myram = vthread.MultibankRAM(m, 'myram', clk, rst, datawidth, addrwidth,
                                 numbanks=numbanks)

    all_ok = m.TmpReg(initval=0)

    block_size = 4
    array_len = 32
    array_size = (array_len + array_len) * 4 * numbanks

    def blink(size):
        all_ok.value = True

        for i in range(4):
            print('# iter %d start' % i)
            # Test for 4KB boundary check
            offset = i * 1024 * 16 + (myaxi.boundary_size - 4)
            body(size, offset)
            print('# iter %d end' % i)

        if all_ok:
            print('ALL OK')

    def body(size, offset):
        # write
        count = 0
        offset = 0
        bias = 0
        while count < size:
            for bank in range(numbanks):
                for i in range(block_size):
                    wdata = bias + i + 100
                    myram.write_bank(bank, offset + i, wdata)
                    count += 1
                bias += block_size
            offset += block_size

        laddr = 0
        gaddr = offset
        myram.dma_write_block(myaxi, laddr, gaddr, size, block_size)
        print('dma_write: [%d] -> [%d]' % (laddr, gaddr))

        # write
        count = 0
        offset = 0
        bias = 0
        while count < size:
            for bank in range(numbanks):
                for i in range(block_size):
                    wdata = bias + i + 1000
                    myram.write_bank(bank, offset + i, wdata)
                    count += 1
                bias += block_size
            offset += block_size

        laddr = 0
        gaddr = array_size + offset
        myram.dma_write_block(myaxi, laddr, gaddr, size, block_size)
        print('dma_write: [%d] -> [%d]' % (laddr, gaddr))

        # read
        laddr = 0
        gaddr = offset
        myram.dma_read_block(myaxi, laddr, gaddr, size, block_size)
        print('dma_read:  [%d] <- [%d]' % (laddr, gaddr))

        count = 0
        offset = 0
        bias = 0
        while count < size:
            for bank in range(numbanks):
                for i in range(block_size):
                    rdata = myram.read_bank(bank, offset + i)
                    if vthread.verilog.NotEql(rdata, bias + i + 100):
                        print('rdata[%d:%d] = %d' % (bank, i, rdata))
                        all_ok.value = False
                    count += 1
                bias += block_size
            offset += block_size

        # read
        laddr = 0
        gaddr = array_size + offset
        myram.dma_read_block(myaxi, laddr, gaddr, size, block_size)
        print('dma_read:  [%d] <- [%d]' % (laddr, gaddr))

        count = 0
        offset = 0
        bias = 0
        while count < size:
            for bank in range(numbanks):
                for i in range(block_size):
                    rdata = myram.read_bank(bank, offset + i)
                    if vthread.verilog.NotEql(rdata, bias + i + 1000):
                        print('rdata[%d:%d] = %d' % (bank, i, rdata))
                        all_ok.value = False
                    count += 1
                bias += block_size
            offset += block_size

    th = vthread.Thread(m, 'th_blink', clk, rst, blink)
    fsm = th.start(array_len)

    return m


def mkTest(memory_datawidth=128):
    m = Module('test')

    # target instance
    led = mkLed(memory_datawidth)

    # copy paras and ports
    params = m.copy_params(led)
    ports = m.copy_sim_ports(led)

    clk = ports['CLK']
    rst = ports['RST']

    memory = axi.AxiMemoryModel(m, 'memory', clk, rst, memory_datawidth)
    memory.connect(ports, 'myaxi')

    uut = m.Instance(led, 'uut',
                     params=m.connect_params(led),
                     ports=m.connect_ports(led))

    simulation.setup_waveform(m, uut)
    simulation.setup_clock(m, clk, hperiod=5)
    init = simulation.setup_reset(m, rst, m.make_reset(), period=100)

    init.add(
        Delay(100000),
        Systask('finish'),
    )

    return m


if __name__ == '__main__':
    test = mkTest()
    verilog = test.to_verilog('tmp.v')
    print(verilog)

    sim = simulation.Simulator(test)
    rslt = sim.run()
    print(rslt)
