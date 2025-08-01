from flask import Flask, request, jsonify, render_template_string, abort
import mysql.connector
from mysql.connector import errorcode

app = Flask(__name__)

# Update this based on your mobile hotspot's IP range
ALLOWED_NETWORK_PREFIX = '192.168.118'

def is_request_from_local_network():
    client_ip = request.remote_addr
    return client_ip.startswith(ALLOWED_NETWORK_PREFIX)

@app.before_request
def restrict_remote_access():
    if not is_request_from_local_network():
        abort(403)  # Forbidden

# MySQL database setup
DATABASE_CONFIG = {
    'user': 'root',
    'password': '16062004@Vi1',
    'host': 'localhost',
    'database': 'sensor_data',
    'raise_on_warnings': True
}

def init_db():
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_values (
                id INT AUTO_INCREMENT PRIMARY KEY,
                value FLOAT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message VARCHAR(255) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

init_db()

@app.route('/update', methods=['GET'])
def update_sensor():
    sensor_value = request.args.get('sensor')
    if sensor_value:
        sensor_value = float(sensor_value)
        try:
            conn = mysql.connector.connect(**DATABASE_CONFIG)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sensor_values (value) VALUES (%s)", (sensor_value,))
            if sensor_value > 97:
                cursor.execute("INSERT INTO alerts (message) VALUES (%s)", (f"Fault value: {sensor_value}",))
            conn.commit()
        except mysql.connector.Error as err:
            print(err)
        finally:
            cursor.close()
            conn.close()
        return 'OK', 200
    return 'Bad Request', 400

@app.route('/sensor_data', methods=['GET'])
def get_sensor_data():
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM sensor_values ORDER BY timestamp DESC LIMIT 100")
        data = cursor.fetchall()
    except mysql.connector.Error as err:
        print(err)
        return 'Internal Server Error', 500
    finally:
        cursor.close()
        conn.close()
    sensor_values = [row[0] for row in data]
    max_value = max(sensor_values) if sensor_values else None
    return jsonify(sensor_values=sensor_values, max_value=max_value)

@app.route('/fault_data', methods=['GET'])
def get_fault_data():
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT message, timestamp FROM alerts ORDER BY timestamp DESC")
        data = cursor.fetchall()
    except mysql.connector.Error as err:
        print(err)
        return 'Internal Server Error', 500
    finally:
        cursor.close()
        conn.close()
    faults = [{'message': row[0], 'timestamp': row[1]} for row in data]
    return jsonify(faults=faults)

@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Sensor Data</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            #myChart {
                width: 80%;
                height: 400px;
            }
            #current-value, #max-value, #all-values, #fault-values {
                margin-top: 20px;
            }
            #all-values {
                white-space: pre-wrap;
            }
            .warning {
                color: red;
            }
        </style>
    </head>
    <body>
        <h1>Live Sensor Data</h1>
        <canvas id="myChart"></canvas>
        <div id="current-value"></div>
        <div id="max-value"></div>
        <div id="all-values"></div>
        <div id="fault-values"></div>
        <div id="warning"></div>
        <script>
            var ctx = document.getElementById('myChart').getContext('2d');
            var sensorValues = [];
            var myChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Sensor Value',
                        data: sensorValues,
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1,
                        fill: false,
                        pointBackgroundColor: 'rgba(75, 192, 192, 0.2)',
                    }]
                },
                options: {
                    scales: {
                        x: {
                            type: 'linear',
                            position: 'bottom',
                            grid: {
                                display: false
                            }
                        },
                        y: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });

            function fetchSensorData() {
                fetch('/sensor_data')
                    .then(response => response.json())
                    .then(data => {
                        console.log('Fetched sensor data:', data);  // Debugging statement

                        sensorValues.length = 0;
                        myChart.data.labels.length = 0;
                        var faultIndices = [];
                        data.sensor_values.forEach((value, index) => {
                            sensorValues.push(value);
                            myChart.data.labels.push(index);

                            if (value > 97) {
                                faultIndices.push(index);
                            }
                        });
                        myChart.update();

                        // Update the current value
                        document.getElementById('current-value').innerText = 'Current sensor value: ' + sensorValues[sensorValues.length - 1];

                        // Update the max value
                        document.getElementById('max-value').innerText = 'Max value in the last 10 values: ' + Math.max(...sensorValues.slice(-10));

                        // Update all values
                        document.getElementById('all-values').innerText = 'All sensor values: ' + sensorValues.join(', ');

                        // Update warnings and highlight points
                        if (faultIndices.length > 0) {
                            var warningMsg = 'Fault occurred at:';
                            faultIndices.forEach(index => {
                                warningMsg += '\\nSensor value ' + sensorValues[index].toFixed(2) + ' at index ' + index;
                            });
                            document.getElementById('warning').innerText = warningMsg;
                            document.getElementById('warning').classList.add('warning');

                            var dataset = myChart.data.datasets[0];
                            var pointBackgroundColors = Array(sensorValues.length).fill('rgba(75, 192, 192, 0.2)');
                            faultIndices.forEach(index => {
                                pointBackgroundColors[index] = 'rgba(255, 0, 0, 0.6)';
                            });
                            dataset.pointBackgroundColor = pointBackgroundColors;
                            myChart.update();
                        } else {
                            document.getElementById('warning').innerText = '';
                            document.getElementById('warning').classList.remove('warning');
                            myChart.data.datasets[0].pointBackgroundColor = 'rgba(75, 192, 192, 0.2)';
                            myChart.update();
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching sensor data:', error);  // Debugging statement
                    });
            }

            setInterval(fetchSensorData, 1000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
