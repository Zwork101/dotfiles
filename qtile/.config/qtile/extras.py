import subprocess

from libqtile.widget.base import ThreadPoolText, PaddingMixin, MarginMixin
from libqtile.lazy import lazy


class PowerWidget(ThreadPoolText):

    SYMBOLS = {
        "power-saver": "\uf295",
        "balanced": "\uf24e",
        "performance": "\ue315"
    }

    def __init__(self, **config):
        super().__init__("\uf244 ?", **config)

        self.add_defaults(PaddingMixin.defaults)
        self.add_defaults(MarginMixin.defaults)
        self.add_callbacks(
            {
                "Button4": self.max_power,
                "Button2": self.med_power,
                "Button5": self.min_power
            }
        )

    def poll(self):
        proc = subprocess.Popen(
            "powerprofilesctl get",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )

        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            return "ERR"
        
        self._power_state = stdout.decode().strip()
        symbol = self.SYMBOLS[self._power_state]

        return "\uf244  " + symbol

    #@lazy.function
    def max_power(self):
        proc = subprocess.run("powerprofilesctl set performance", shell=True)
        self.update(self.poll())

    #@lazy.function
    def min_power(self):
        proc = subprocess.run("powerprofilesctl set power-saver", shell=True)
        self.update(self.poll())

    #@lazy.function
    def med_power(self):
        proc = subprocess.run("powerprofilesctl set balanced", shell=True)
        self.update(self.poll())

# w = PowerWidget()
# import pdb; pdb.set_trace()