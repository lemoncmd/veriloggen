from __future__ import absolute_import
from __future__ import print_function
import sys
import os

# the next line can be removed after installation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from veriloggen import *
import veriloggen.thread as vthread


def mkLed(numthreads=8):
    m = Module('blinkled')
    clk = m.Input('CLK')
    rst = m.Input('RST')
    led = m.OutputReg('LED', 8)

    datawidth = 32
    addrwidth = 4
    myfifo = vthread.FIFO(m, 'myfifo', clk, rst, datawidth, addrwidth)

    def myfunc(tid):
        myfifo.lock()
        print("Thread %d Lock" % tid)

        read_data = myfifo.deq()
        print("Thread %d fifo.out = %d" % (tid, read_data))

        write_data = read_data + 1
        myfifo.enq(write_data)
        print("Thread %d fifo.in <- %d" % (tid, write_data))

        read_data = myfifo.deq()
        print("Thread %d fifo.out = %d" % (tid, read_data))

        write_data = read_data + 1
        myfifo.enq(write_data)
        print("Thread %d fifo.in <- %d" % (tid, write_data))

        myfifo.unlock()
        print("Thread %d Unlock" % tid)

    def blink():
        myfifo.enq(100)
        myfifo.enq(200)

        for tid in range(numthreads):
            pool.run(tid, tid)

        for tid in range(numthreads):
            pool.join(tid)

        read_data = myfifo.deq()
        led.value = read_data
        print("result fifo.out = %d" % read_data)

        read_data = myfifo.deq()
        led.value = read_data
        print("result fifo.out = %d" % read_data)

    th = vthread.Thread(m, clk, rst, 'th_blink', blink)
    pool = vthread.ThreadPool(m, clk, rst, 'th_myfunc', myfunc, numthreads)
    fsm = th.start()

    return m


def mkTest():
    m = Module('test')

    # target instance
    led = mkLed()

    # copy paras and ports
    params = m.copy_params(led)
    ports = m.copy_sim_ports(led)

    clk = ports['CLK']
    rst = ports['RST']

    uut = m.Instance(led, 'uut',
                     params=m.connect_params(led),
                     ports=m.connect_ports(led))

    simulation.setup_waveform(m, uut)
    simulation.setup_clock(m, clk, hperiod=5)
    init = simulation.setup_reset(m, rst, m.make_reset(), period=100)

    init.add(
        Delay(10000),
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
