import json
import os
import requests
from datetime import datetime, timedelta
from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)


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


# Function to generate log to insert into page
# Retrieves data from ThingSpeak
def create_log(field):
    # Check field to determine trigger value
    # Moisture sensor = 0, low moisture actuator triggers
    # LED = 1, means LED is on
    if field == 2:
        trigger_value = '0'
    elif field == 3:
        trigger_value = '1'

    log = '<ul class="list-group">' 

    resp = requests.get(f'https://api.thingspeak.com/channels/1624174/fields/{field}.json?api_key=****')
    results = json.loads(resp.text)

    for result in results['feeds']:
        if result[f'field{field}'] == trigger_value:
            unformatted_date = result['created_at'] # Code here is to convert ThingSpeak date format to our desired format
            date_object = datetime.strptime(unformatted_date, '%Y-%m-%dT%H:%M:%SZ')
            date_object += timedelta(hours=8) # ThingSpeak returns time in GMT, need to +8h for local time
            formatted_date = date_object.strftime("%d/%m/%Y %H:%M:%S")

            log += f'<li class="list-group-item"><i class="fas fa-exclamation-triangle text-danger"></i>{formatted_date}</li>' 

    log += '</ul>' 

    return log


# Function to write to configuration file
def write_config(config):
    try:
        with open('config.json', 'w') as f:
            f.write(config)

        return
    except:
        print('Error reading configuration file, exiting program...')
        os._exit(1)


# Endpoint for main page
@app.route('/')
def index():
    min_light_level, watering_duration, interval = read_config() 
    led_log = create_log(3) 
    water_log = create_log(2) 

    return render_template('index.html', min_light_level=min_light_level, watering_duration=watering_duration, interval=interval, led_log=led_log, water_log=water_log)


# Endpoint for editing configuration
@app.route('/edit', methods=['POST'])
def edit():
    config = request.get_json() 
    config = json.dumps(config) 
    write_config(config) 

    return 'success'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

