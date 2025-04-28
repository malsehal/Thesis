class SimulationLogger:
    def __init__(self):
        self.events = []
    def log_event(self, message):
        self.events.append(message)
        # print(message)
