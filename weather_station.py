import time
import pigpio

class PigpioBitBang:
	"""PIGPIO Bitbang I2C Helper Class"""
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
		(count, data) = self.pi.bb_i2c_zip(self.SDA, [self.BB_ADDRESS, address, self.BB_START, 
						self.BB_WRITE, len(data_array)+1, pointer_reg] + \
						data_array + [self.BB_STOP, self.BB_END])
		return data

	def close_bus(self):
		self.pi.bb_i2c_close(self.SDA)

class RepeatStart(PigpioBitBang):
	"""Repeated start hack for TI HDC1050"""
	def pr_read(self, address, pointer_reg, read_bytes):
		(count, data) = pi.bb_i2c_zip(SDA, [BB_ADDRESS, address,
					{BB_START, BB_WRITE, BB_ESCAPE, pointer_reg, 
					BB_START, BB_READ, read_bytes, BB_STOP, BB_END])
		return data

# # abstract sensor base class
# class sensor(metaclass=ABCMeta):
# 	def init
# 	def read
# 	def write

class Altitude:
	"""Freescale XXXXX Driver"""
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
		self.bb_channel = PigpioBitBang()
		self.bb_channel.open_bus()
		self.bb_channel.write(self.ALT_I2C, self.CONTROL_REG_ADDR, self.BAR_OSR_128)
		self.bb_channel.write(self.ALT_I2C, self.DATA_FLAG_ADDR, self.ENABLE_DATA_FLAG)
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

class Ti:
	"""TI HDC1050 Driver"""
	HUM_I2C = 0x40
	CONTROL_REG_ADDR = 0x02
	SETUP = 0x02
	READ_ADDR = 0x00

	def __init__(self):
		self.bb_channel = PigpioBitBang()
		self.bb_channel.open_bus()
		self.bb_channel.write(self.HUM_I2C, self.CONTROL_REG_ADDR, self.SETUP)

	def ready(self):
		pass

	def get_data(self):
		pass

	def package_output(self):
		pass

	def close_channel(self):
		self.bb_channel.close_bus()


if __name__ == "__main__":
	freescale = Altitude()
	for i in range(5000):
		raw = freescale.get_data()
		(press,temp) = freescale.package_output(raw)
		print(press, temp)
		try:
			time.sleep(1)
		except KeyboardInterrupt:
			freescale.close_channel()
			break


# def init_hum():
# 	bb_write(HUM_I2C, H_CONTROL_REG_ADDR, SETUP)
# 	print("The thing we're reading: %r" % (bb_pr_read(HUM_I2C, 0xFB, 0x04),))

# def read_hum():
# 	# initialize measurement
# 	(count, data) = pi.bb_i2c_zip(SDA, [BB_ADDRESS, HUM_I2C,
# 				BB_START, BB_WRITE, BB_ESCAPE, READ_ADDR, BB_STOP, BB_END])

# 	time.sleep(0.5)

# 	# read measurement
# 	(count, data) = pi.bb_i2c_zip(SDA, [BB_ADDRESS, HUM_I2C,
# 				BB_START, BB_READ, 2, BB_STOP, BB_END])

# 	raw_humidity = bb_pr_read(HUM_I2C, READ_ADDR+1, 0x02)

# 	print("temp data: %r  humidity data: %r" % (data, raw_humidity))
# 	# if len(raw) != 4:
# 	# 	return (None, None)
# 	temperature = int.from_bytes(data[0:2 >> 2], byteorder='big', signed=False)
# 	humidity = int.from_bytes(raw_humidity[2:4] >> 2, byteorder='big', signed=False)
# 	print(temperature, humidity)
# 	return (temperature, humidity)
