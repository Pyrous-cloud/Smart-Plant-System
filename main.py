import json
import os
import requests
import spidev
import RPi.GPIO as GPIO
from datetime import datetime
from time import sleep

GPIO.setmode(GPIO.BCM) 
GPIO.setwarnings(False) 

GPIO.setup(24, GPIO.OUT) # LED
GPIO.setup(4, GPIO.IN) # Moisture sensor
GPIO.setup(26, GPIO.OUT) # Servo Motor

led_pwm = GPIO.PWM(24, 50) 
servo_motor_pwm = GPIO.PWM(26, 50) 

spi = spidev.SpiDev() 
spi.open(0, 0) 


# Function to read configuration from file
def read_config():
    try:
        with open('config.json', 'r') as f:
            config = f.read()
            config = json.loads(config)
            min_light_level = config['min_light_level']
            watering_duration = config['watering_duration']
            interval = config['interval']

        return min_light_level, watering_duration, interval
    except:
        print('Error reading configuration file, exiting program...')
        os._exit(1)


# Function to read LDR value
def read_ldr(adcnum):
    if adcnum > 7 or adcnum < 0:
        return -1
    
    spi.max_speed_hz = 1350000
    r = spi.xfer2([1, 8 + adcnum << 4, 0])
    data = ((r[1] & 3) << 8)+r[2]

    return data


# Function to get date and time
def get_datetime():
    date_object = datetime.now()
    # dd/mm/YY H:M:S
    formatted_date = date_object.strftime("%d/%m/%Y %H:%M:%S")
    
    return formatted_date


# Function to check the light level and turn on/off the LED
def check_light_level(min_light_level, ldr_light_level):
    # If light level exceeds minimum light level turn LED on with PWM
    if min_light_level >= ldr_light_level:
        print('Low light levels detected, turning LED on...')
        led_duty_cycle = 100 - ldr_light_level
        led_pwm.start(led_duty_cycle)

        resp = requests.post('https://api.thingspeak.com/apps/thingtweet/1/statuses/update',
                json={"api_key":"****","status":f"{get_datetime()}: Alert, low light levels detected. LED has been turned on."}) # Tweet to owner
        
        return 1
    else:
        print('High light levels detected, turning LED off...')
        led_pwm.stop()

        return 0


# Function to check the moisture level and turn on/off the actuator for x amount of seconds
def check_moisture_level(watering_duration):
    if (GPIO.input(4)):
        print('High moisture levels detected...')
        
        return 1
    else:
        print('Low moisture levels detected...')
        print(f'Watering plants for {watering_duration}s...')

        servo_motor_pwm.start(7) 
        sleep(watering_duration) 
        servo_motor_pwm.start(2)
        sleep(1) 
        resp = requests.post('https://api.thingspeak.com/apps/thingtweet/1/statuses/update',
            json={"api_key":"****","status":f"{get_datetime()}: Alert, low moisture levels detected. Plants are being watered now."}) # Tweet to owner

        return 0


# Main function
def main():
    config_last_modified_time = 0
    
    while (True):
        # Check if config has been updated
        print('Checking configuration...')
        if config_last_modified_time != os.path.getmtime('config.json'):
            config_last_modified_time = os.path.getmtime('config.json')
            min_light_level, watering_duration, interval = read_config() 

            print('New configuration detected...')
            print(f'New values are minimum light level: {min_light_level}, watering duration: {watering_duration}, interval: {interval}.')

        # Code for lighting feature
        print('Checking light levels...')
        ldr_value = read_ldr(0) # Retrieve LDR value (ADC channel 0)
        ldr_light_level = ldr_value / 1023 * 100 # Convert LDR value into percentage
        print(f'LDR value: {ldr_value}, Light level percentage: {ldr_light_level}')
        led_on = check_light_level(min_light_level, ldr_light_level) #  
        
        # Code for watering feature
        print('Checking moisture levels...')
        moisture_level = check_moisture_level(watering_duration)
        resp = requests.get(f'https://api.thingspeak.com/update?api_key=****&field1={ldr_light_level}&field2={moisture_level}&field3={led_on}') # Send sensor data to the cloud

        print(f'Loop finished, repeating in {interval}s...')
        sleep(interval) # 


if __name__ == '__main__':
    main()


# Notes:
# Check if actuator turn off itself
