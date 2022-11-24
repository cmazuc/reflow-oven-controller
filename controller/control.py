import datetime
import json
from time import sleep

import matplotlib.animation as animation
import matplotlib.pyplot as plot
import serial

ON_COMMAND = b"e"
OFF_COMMAND = b"d"

PROFILE_STEP = 15  # seconds

# target temperatures, every PROFILE_STEP
PROFILES = {
    "Sn42Bi57Ag1": [
        35,
        35,
        40,
        50,
        50,
        60,
        80,
        95,
        110,
        117,
        125,
        135,
        145,
        157,
        180,
        180,
        180,
        180,
        0,
    ],
    "Sn63Pb37": [
        35,
        35,
        40,
        60,
        95,
        100,
        110,
        120,
        130,
        140,
        150,
        165,
        180,
        200,
        215,
        230,
        235,
        230,
        180,
        50,
        0,
    ],
}


class Profile:
    def __init__(self, profile):
        self.profile = profile

        self.plot_time = list(range(0, len(profile) * PROFILE_STEP, PROFILE_STEP))
        self.plot_temperature = [temperature for temperature in self.profile]

        self.max_temperature = 0

        for temperature in self.plot_temperature:
            if temperature > self.max_temperature:
                self.max_temperature = temperature

    def target_temperature(self, time):
        """
        Determine the target temperature for any given point in the profile. 

        time is the number of seconds since the start of the profile.
        """
        
        for index in range(0, len(self.profile)):
            offset = index * PROFILE_STEP

            if time > offset:
                continue

            if index == 0:
                last_offset = 0
                last_temperature = 0
            else:
                last_offset = offset - PROFILE_STEP
                last_temperature = self.profile[index - 1]

            temperature = self.profile[index]

            x = offset - last_offset
            y = temperature - last_temperature

            slope = float(y) / float(x) if x else 0

            return temperature + (slope * (time - offset))

        return 0

    @property
    def length(self):
        return self.plot_time[-1]

    @property
    def plot_series(self):
        x = []
        y = []

        for offset in range(0, self.length):
            x.append(offset)
            y.append(self.target_temperature(offset))

        return (x, y)


class ReflowController:
    def __init__(self, device, lag_time, baudrate=9600):
        print(f"Initializing serial device {device} at {baudrate} baud")
        self._initalized = False

        self.device = device
        self.lag_time = lag_time
        self.serial = serial.Serial(device, baudrate)

        self.profile = None
        self.plot_temperature = []
        self.plot_time = []
        self.elapsed = 0
        self.start = 0

        self.temperature = 0
        self.oven_on = False
        self.oven_status = False
        self.oven_on_time = 0
        self.oven_off_time = 0
        self.fault = 0
        self.last_wait = 0

        self.off()
        self.update_status()
        self._initalized = True

    def __del__(self):
        self.off()
        self.serial.flush()
        self.serial.close()

    @property
    def _now(self):
        return datetime.datetime.utcnow().timestamp()

    def read(self):
        self.serial.reset_input_buffer()

        try:
            return self.serial.readline().strip().decode("utf-8")
        except UnicodeDecodeError:
            pass

    def write(self, line):
        self.serial.reset_output_buffer()

        self.serial.write(line)

    def on(self):
        self.write(ON_COMMAND)

        if not self.oven_on:
            self.oven_on_time = self._now

        self.oven_on = True

    def off(self):
        self.write(OFF_COMMAND)

        if self.oven_on:
            self.oven_off_time = self._now

        self.oven_on = False

    def reset(self):
        self.elapsed = 0
        self.start = self._now
        self.plot_temperature = []
        self.plot_time = []
        self.off()

    def plot(self):
        self.plot_temperature.append(self.temperature)
        self.plot_time.append(self.elapsed)

    def update_status(self):
        self.elapsed = self._now - self.start

        line = self.read()

        if line:
            try:
                status = json.loads(line)
            except ValueError as e:
                return

            self.temperature = status["t"]
            self.fault = status["f"]
            self.oven_status = False if status["s"] == 0 else True
            self.last_wait = status["w"]

            self.plot()

            return status

    def print_status(self, target, target_velocity=None):
        delta = self.temperature - target

        if delta > 50:
            print("OPEN DOOR!! / ", end="")

        print(f"Oven On: {self.oven_on} / ", end="")
        print(f"Temp: {self.temperature:.1f}C / ", end="")
        print(f"Target: {target:.1f}C / ", end="")
        print(f"Delta: {delta:.1f}C / ", end="")

        if target_velocity:
            print(f"Target Velocity: {target_velocity:.1f} / ", end="")

        print(f"Velocity: {self.velocity if self.velocity else 0:.1f}C/s")

    def cooldown(self, target=35):
        while not self.update_status():
            pass

        self.off()

        while int(target) < int(self.temperature):
            if self.update_status():
                print(
                    f"{self.temperature:.1f}C is over start temperature {target:.1f}C, waiting for cool down ({self.velocity if self.velocity else 0:.1f} C/s)"
                )

        self.reset()

    @property
    def velocity(self):
        period = 3  # sample this many seconds to determine velocity in degrees C/s

        try:
            last = self.plot_time[-1]
        except IndexError:
            return None

        for index, time in reversed(list(enumerate(self.plot_time))):
            if last - time > period:
                return (self.plot_temperature[index] - self.plot_temperature[-1]) / (
                    self.plot_time[index] - self.plot_time[-1]
                )

        return None

    def load_profile(self, profile):
        self.reset()

        self.profile = Profile(profile)

    def run_profile(self):
        target = self.profile.target_temperature(self.elapsed)

        if not self.update_status():
            return

        if self.fault:
            print(f"Fault detected! {self.fault}")
            self.off()

            return

        # Look ahead lag_time seconds in the profile and calculate the target temperature
        next_target = self.profile.target_temperature(self.elapsed + self.lag_time)

        # Given the current temperature, calculate the velocity required to reach the next target
        # in lag_time seconds
        target_velocity = (next_target - self.temperature) / self.lag_time

        if self.velocity is not None and self.velocity < target_velocity:
            self.on()
        else:
            self.off()

        self.print_status(target, target_velocity)


if __name__ == "__main__":
    oven = ReflowController(device="/dev/ttyACM0", lag_time=25)

    oven.cooldown()
    oven.load_profile(PROFILES["Sn42Bi57Ag1"])

    figure = plot.figure()
    figure.canvas.manager.set_window_title("Reflow Oven")

    axes = plot.axes(
        xlim=(0, oven.profile.length + 30),
        ylim=(0, max(250, oven.profile.max_temperature + 50)),
    )

    oven_plot = plot.plot([], [], "r")[0]
    profile_plot = plot.plot(*oven.profile.plot_series)[0]

    def run(_):
        oven.run_profile()

        oven_plot.set_data(oven.plot_time, oven.plot_temperature)

    ani = animation.FuncAnimation(figure, run)
    plot.show(block=True)
