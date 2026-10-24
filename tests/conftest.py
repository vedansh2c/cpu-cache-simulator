import pytest
from app.metrics import BEGIN, END


@pytest.fixture
def stats_text():
    # Synthetic unit-test input, never exposed as a simulation result.
    return f"""{BEGIN}
simSeconds 0.000002
simFreq 1000000000000
system.cpu.numCycles 4000
system.cpu.numInsts 1000
system.cpu.icache.overallMissRate::total 0.05
system.cpu.dcache.overallMissRate::total 0.2
system.cpu.dcache.overallAvgMissLatency::total 1000
system.l2cache.overallMissRate::total 0.1
system.mem_ctrl.dram.avgMemAccLat 50000
system.mem_ctrl.dram.dramBytesRead 128
system.mem_ctrl.dram.dramBytesWritten 64
{END}
"""
