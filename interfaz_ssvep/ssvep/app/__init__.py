import builtins

from ssvep.app.settings import Settings

builtins.APP_NAME            = 'SSVEP'
builtins.APP_VERSION         = '1.0'
builtins.ADC_VREF            = 4.5 # ADS1299 Reference input voltage
builtins.PGA_GAIN            = 12  # ADS1299 Amplifier gain #tenia 12
builtins.MV_VALUE            = 1 / (builtins.ADC_VREF / (pow(2, 23) - 1) / builtins.PGA_GAIN) / 1_000 # Formula de OpenBCI
builtins.CHANNELS_NUMBER     = 8   # ADS1299 Max chanels
builtins.SAMPLE_RATE         = 250#250 # ADS1299 Data rate
builtins.BA_SERIAL_BAUDRATE  = 921600 # BioAmp Baudrate
builtins.BCI_SERIAL_BAUDRATE = 115200 # OpenBCI Baudrate
builtins.SETTINGS            = Settings()
