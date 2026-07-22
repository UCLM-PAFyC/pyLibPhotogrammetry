# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

class Calibration:
    def __init__(self,
                 sensor):
        self.sensor = sensor
        self.type = None
        self.kind = None
        self.height = self.sensor.height
        self.width = self.sensor.width
        self.parameters = {}
