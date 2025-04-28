import random
from config.parameters import MIN_BW_REQUEST, MAX_BW_REQUEST, MIN_DURATION, MAX_DURATION

def sample_poisson(lam):
    L = 2.71828 ** (-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1

def random_request_parameters():
    # For a one-square environment, assume 4 nodes (IDs 0 to 3).
    node_id = random.randint(0, 3)
    bw = random.randint(MIN_BW_REQUEST, MAX_BW_REQUEST)
    duration = random.randint(MIN_DURATION, MAX_DURATION)
    device_type = "5G" if random.random() < 0.6 else "IoT"
    return (node_id, bw, duration, device_type)