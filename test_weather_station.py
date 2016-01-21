import pytest
import weather_station as ws

# @pytest.fixture()
# def MPL3115A2:
# 	test_device = ws.Altitude()

# @pytest.fixture()
# def HDC1050:
# 	test_device = ws.Humidity()

def test_PointerWrite():
	#grab hdc and mpl manufacturer ID registers and read back

	#Constants
	ALT = 0x60
	HUM = 0x40
	ALT_REG = 0x0C #who am i 
	HUM_REG = 0xFF
	ALT_EXPECT = 0x0000
	HUM_EXPECT = 0x1050 #b' \x10x\50'
	ALT_BYTES = 0x02 
	HUM_BYTES = 0x04

	test_device = ws.PointerWrite()
	test_device.open_bus()
	alt_out = test_device.read(ALT, ALT_REG, ALT_BYTES)
	hum_out = test_device.read(HUM, HUM_REG, HUM_BYTES)

	assert alt_out == ALT_EXPECT
	assert hum_out == HUM_EXPECT

def test_WeatherStation():
	#San Francisco test Winter 2016

	#Test Ranges
	low_h = 20
	high_h = 80
	low_t = 0
	high_t = 32
	low_p = 10000
	high_p = 40000
	low_a = 10
	high_a = 10000

	test_device = ws.WeatherStation()

	h_out = test_device.HDC1050_humidity()
	assert(low_h<h_out<high_h)
	t_out = test_device.HDC1050_temperature()
	assert(low_t<h_out<high_t)
	p_out = test_device.MPL3115A2_pressure()
	assert(low_p<p_out<high_p)
	t2_out = test_device.MPL3115A2_temperature()
	assert(low_t<t2_out<high_t)
	a_out = test_device.MPL3115A2_altitude()
	assert(low_a<a_out<high_a)
