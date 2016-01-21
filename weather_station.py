import time
import argparse

import pigpio

class PigpioI2CBitBang:
	"""PIGPIO Bitbang I2C Helper Class
	Standard implementations of I2C Write and Read.

	read(i2c address, pointer register, number of bytes to read)
	write(i2c address, pointer register, data in array)

	"""
	SDA = 6
	SCL = 13
	CF = 100000

	# PIGPIO BB INTERFACE
	BB_END = 0
	BB_ESCAPE = 1
	BB_START = 2
	BB_STOP = 3
	BB_ADDRESS = 4
	BB_FLAGS = 5
	BB_READ = 6
	BB_WRITE = 7

	def __init__(self):
		self.pi = pigpio.pi()

	def open_bus(self):
		self.handle = self.pi.bb_i2c_open(self.SDA, self.SCL, self.CF)

	def read(self, address, pointer_reg, read_bytes):
		read_bytes += 1
		(count, data) = self.pi.bb_i2c_zip(self.SDA, [self.BB_ADDRESS, address,
					self.BB_START, self.BB_WRITE, self.BB_ESCAPE, pointer_reg,
					self.BB_START, self.BB_READ, read_bytes, self.BB_STOP, self.BB_END])
		return data

	def write(self, address, pointer_reg, data_array):
		if type(data_array) is int:
			assert data_array < 256
			data_array = [data_array]
		(count, data) = self.pi.bb_i2c_zip(self.SDA, [self.BB_ADDRESS, address, 
					self.BB_START, self.BB_WRITE, len(data_array)+1, pointer_reg] + \
					data_array + [self.BB_STOP, self.BB_END])
		return data

	def close_bus(self):
		self.pi.bb_i2c_close(self.SDA)

class PointerWrite(PigpioI2CBitBang):
	"""I2C Hack for TI HDC1050"""
	def pr_write(self, address, pointer_reg):
		(count, data) = self.pi.bb_i2c_zip(self.SDA, [self.BB_ADDRESS, address,
					self.BB_START, self.BB_WRITE, self.BB_ESCAPE, pointer_reg, 
					self.BB_STOP, self.BB_END])
		return (count, data)

	def pr_read(self, address, read_bytes):
		(count, data) = self.pi.bb_i2c_zip(self.SDA, [self.BB_ADDRESS, address,
		 			self.BB_START, self.BB_READ, read_bytes, self.BB_STOP, 
		 			self.BB_END])
		return (count, data)

class Altitude:
	"""Freescale MPL3115A2 Driver"""
	ALT_I2C = 0x60
	CONTROL_REG_ADDR = 0x26
	ALT_OSR_128 = 0xB8
	BAR_OSR_128 = 0x28
	DATA_FLAG_ADDR = 0x13
	ENABLE_DATA_FLAG = 0x07
	ALT_ENABLE = 0xB9
	BAR_ENABLE = 0x29
	STATUS_REG = 0x00
	P_MSB = 0x01
	STATUS_RDY = 3

	def __init__(self):
		self.bb_channel = PigpioI2CBitBang()
		self.bb_channel.open_bus()
		self.bb_channel.write(self.ALT_I2C, self.DATA_FLAG_ADDR, self.ENABLE_DATA_FLAG)

	def set_altitude(self):
		self.bb_channel.write(self.ALT_I2C, self.CONTROL_REG_ADDR, self.ALT_OSR_128)
		self.bb_channel.write(self.ALT_I2C, self.CONTROL_REG_ADDR, self.ALT_ENABLE)

	def set_barometric(self):
		self.bb_channel.write(self.ALT_I2C, self.CONTROL_REG_ADDR, self.BAR_OSR_128)
		self.bb_channel.write(self.ALT_I2C, self.CONTROL_REG_ADDR, self.BAR_ENABLE)

	def ready(self):
		data = self.bb_channel.read(self.ALT_I2C, self.STATUS_REG, 1)
		if len(data) > 0 and data[0] & (1<<self.STATUS_RDY):
			return True
		return False

	def get_data(self):
		if not self.ready():
			return (None, None)
		raw = self.bb_channel.read(self.ALT_I2C, self.P_MSB, 5)
		return raw

	def package_output(self, raw):
		if len(raw) != 6:
			return (None, None)
		pressure = int.from_bytes(raw[0:2], byteorder='big', signed=False)
		pressure_decimal = (raw[3] >> 4)/10.0

		temp = int.from_bytes(raw[3:4], byteorder='big', signed=False)
		temp_decimal = (raw[4] >> 4)/10.0
		return (pressure+pressure_decimal, temp+temp_decimal)

	def close_channel(self):
		self.bb_channel.close_bus()

class Humidity:
	"""TI HDC1050 Driver"""
	HUM_I2C = 0x40
	CONTROL_REG_ADDR = 0x02
	READ_REG = 0x00
	SETUP = [0x10, 0x00]
	READ_BYTES = 0x04

	def __init__(self):
		self.bb_channel = PointerWrite()
		self.bb_channel.open_bus()
		self.bb_channel.write(self.HUM_I2C, self.CONTROL_REG_ADDR, self.SETUP)
		self.bb_channel.pr_write(self.HUM_I2C, self.READ_REG)

	def ready(self):
		(count, data) = self.bb_channel.pr_read(self.HUM_I2C, self.READ_BYTES)
		if count < 0:
			return False
		return True

	def get_data(self):
		(count, data) = self.bb_channel.pr_read(self.HUM_I2C, self.READ_BYTES)
		return data

	def package_output(self, raw):
		temp = int.from_bytes(raw[0:2], byteorder='big', signed=False)
		hum = int.from_bytes(raw[2:4], byteorder='big', signed=False)
		return (temp, hum)

	def convert_temp(self, raw):
		return float("%.1f"%((raw/(2**16))*165-40))

	def convert_hum(self, raw):
		return float("%.1f"%(raw/(2**16)*100))

	def close_channel(self):
		self.bb_channel.close_bus()

class WeatherStation:
	"""WeatherStation API for 21 Bitcoin Computer expansion board"""

	def HDC1050_humidity(self):
		"""Returns current measured humidity as a percentage."""
		ti = Humidity()
		while ti.ready() == False:
			time.sleep(1)
		raw = ti.get_data()
		(temp, hum) = ti.package_output(raw)
		hum = ti.convert_hum(hum)
		ti.close_channel()
		return(hum)

	def HDC1050_temperature(self):
		"""Returns current measured temperature in degrees C."""
		ti = Humidity()
		while ti.ready() == False:
			time.sleep(1)
		raw = ti.get_data()
		(temp, hum) = ti.package_output(raw)
		temp = ti.convert_temp(temp)
		ti.close_channel()
		return(temp)

	def MPL3115A2_pressure(self):
		"""Returns current barometric pressure in Pascals."""
		freescale = Altitude()
		freescale.set_barometric()
		raw = freescale.get_data()
		(press,temp) = freescale.package_output(raw)
		while press == None:
			time.sleep(1)
			raw = freescale.get_data()
			(press,temp) = freescale.package_output(raw)
		freescale.close_channel()
		return(press)

	def MPL3115A2_temperature(self):
		"""Returns current measured temperature in degrees C."""
		freescale = Altitude()
		freescale.set_barometric()
		raw = freescale.get_data()
		(press,temp) = freescale.package_output(raw)
		while press == None:
			time.sleep(1)
			raw = freescale.get_data()
			(press,temp) = freescale.package_output(raw)
		freescale.close_channel()
		return(temp)

	def MPL3115A2_altitude(self):
		"""Returns current measured altitudea in meters."""
		freescale = Altitude()
		freescale.set_altitude()
		raw = freescale.get_data()
		(alt,temp) = freescale.package_output(raw)
		while alt == None:
			time.sleep(1)
			raw = freescale.get_data()
			(alt,temp) = freescale.package_output(raw)
		freescale.close_channel()
		return(alt)

"""Main execution"""
if __name__ == "__main__":
	""" Command line parser to choose between alt and hum measurement """
	parser = argparse.ArgumentParser(description='Choose between Alt/Bar and Hum measurements')
	parser.add_argument('--measure', help='--measure alt, --measure hum')
	args = parser.parse_args()

	ws_cmd_line = WeatherStation()

	HUM_EN = 0
	ALT_EN = 0
	if args.measure == "hum":
		HUM_EN = 1
	if args.measure == "alt":
		ALT_EN = 1

	if ALT_EN == 1:
		print("MPL3115A2")
		print("Barometric Pressure %.1f Pa" % ws_cmd_line.MPL3115A2_pressure())
		print("Altitude %.1f Meters" % ws_cmd_line.MPL3115A2_altitude())
		print("Temperature %.1f degC" %ws_cmd_line.MPL3115A2_temperature())

	""" Measure Humidity """
	if HUM_EN == 1:
		print("HDC1050")
		print("Humidity %.1f %%" % ws_cmd_line.HDC1050_humidity())
		print("Temperature %.1f degC" %ws_cmd_line.HDC1050_temperature())