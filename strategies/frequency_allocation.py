"""
Implements frequency allocation strategies for different frequency plans.
"""
from config.parameters import TOTAL_BANDWIDTH_MHZ, FREQ_BASE_MHZ

class LargeBlockAllocator:
    def __init__(self, block_size=200):
        self.block_size = block_size

    def find_allocation(self, active_assignments, requested_bw, arch_policy):
        if requested_bw > self.block_size:
            return None  # Request exceeds block size.
        available_blocks = []
        num_blocks = TOTAL_BANDWIDTH_MHZ // self.block_size
        for i in range(num_blocks):
            start = FREQ_BASE_MHZ + i * self.block_size
            available_blocks.append((start, start + self.block_size))
        used = []
        for assignment in active_assignments:
            used.append((assignment.freq_start, assignment.freq_end))
        for block in available_blocks:
            if block not in used:
                return block
        return None

class SubChannelAllocator:
    def __init__(self, channel_size=40):
        self.channel_size = channel_size

    def find_allocation(self, active_assignments, requested_bw, arch_policy):
        num_channels = TOTAL_BANDWIDTH_MHZ // self.channel_size
        channels = []
        for i in range(num_channels):
            start = FREQ_BASE_MHZ + i * self.channel_size
            channels.append((start, start + self.channel_size))
        needed_channels = -(-requested_bw // self.channel_size)  # Ceiling division.
        for i in range(num_channels - needed_channels + 1):
            candidate = channels[i:i+needed_channels]
            candidate_block = (candidate[0][0], candidate[-1][1])
            conflict = False
            for assignment in active_assignments:
                if not (assignment.freq_end < candidate_block[0] or assignment.freq_start > candidate_block[1]):
                    conflict = True
                    break
            if not conflict:
                return candidate_block
        return None

class FreqSlicingAllocator:
    def find_allocation(self, active_assignments, requested_bw, arch_policy):
        start = FREQ_BASE_MHZ
        while start + requested_bw <= FREQ_BASE_MHZ + TOTAL_BANDWIDTH_MHZ:
            candidate = (start, start + requested_bw)
            conflict = False
            for assignment in active_assignments:
                if not (assignment.freq_end < candidate[0] or assignment.freq_start > candidate[1]):
                    conflict = True
                    break
            if not conflict:
                return candidate
            start += 1  # Shift by 1 MHz.
        return None

def get_frequency_allocator(freq_plan):
    if freq_plan == "Large_Blocks":
        return LargeBlockAllocator()
    elif freq_plan == "Sub-Channels":
        return SubChannelAllocator()
    elif freq_plan == "Freq-Slicing":
        return FreqSlicingAllocator()
    else:
        return None