import os
import sys
from datetime import datetime
import ftplib
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# 環境変数をロード
APP_PATH = (
    sys._MEIPASS
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
load_dotenv(os.path.join(APP_PATH, '.env'))

# FTPサーバーの接続情報
ftp_server = os.environ['FTPHOST']
ftp_user = os.environ['FTPUSER']
ftp_password = os.environ['FTPPASS']
ftp_path = os.environ['FTPPATH']

TOTAL_CAPACITY_GB = 40  # 全体の容量は40GB

def get_total_size(ftp, path):
    total_size = 0

    def accumulate_size(line):
        nonlocal total_size
        parts = line.split(maxsplit=8)
        if len(parts) < 9:
            return
        try:
            size = int(parts[4])
            total_size += size
        except ValueError:
            pass

    def is_directory(line):
        return line.startswith('d')

    def get_name(line):
        parts = line.split(maxsplit=8)
        if len(parts) < 9:
            return None
        return parts[8]

    def get_directory_size(ftp, path):
        nonlocal total_size
        lines = []
        try:
            ftp.cwd(path)
            ftp.dir(lines.append)
        except ftplib.error_perm as e:
            if str(e).startswith('505'):
                return
            else:
                raise e
        for line in lines:
            if is_directory(line):
                dir_name = get_name(line)
                if dir_name and dir_name not in ['.', '..']:
                    get_directory_size(ftp, f"{path}/{dir_name}")
            else:
                accumulate_size(line)

    get_directory_size(ftp, path)
    return total_size

def list_directories(ftp, dir_path):
    directories = []
    ftp.cwd(dir_path)
    items = ftp.nlst()
    for item in items:
        try:
            ftp.cwd(item)
            directories.append(item)
            ftp.cwd('..')
        except ftplib.error_perm:
            pass
    return directories

def update_directory_sizes():
    ftp = ftplib.FTP(ftp_server)
    ftp.login(ftp_user, ftp_password)
    subdirectories = list_directories(ftp, ftp_path)
    sizes = {}
    total_size = 0
    for subdir in subdirectories:
        subdir_path = f"{ftp_path}/{subdir}/mail"
        subdir_size = get_total_size(ftp, subdir_path)
        sizes[subdir] = subdir_size / (1024 * 1024)
        total_size += subdir_size

    total_size_mb = total_size / (1024 * 1024)
    total_size_gb = total_size_mb / 1024
    usage_percentage = (total_size_gb / TOTAL_CAPACITY_GB) * 100

    ftp.quit()

    app.config['DIRECTORY_SIZES'] = sizes
    app.config['TOTAL_SIZE_GB'] = total_size_gb
    app.config['USAGE_PERCENTAGE'] = usage_percentage
    app.config['LAST_UPDATED'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"Directory sizes updated at {app.config['LAST_UPDATED']}")
    

@app.route('/')
def index():
    sizes = app.config.get('DIRECTORY_SIZES', {})
    total_size_gb = app.config.get('TOTAL_SIZE_GB', 0)
    usage_percentage = app.config.get('USAGE_PERCENTAGE', 0)
    sorted_sizes = dict(sorted(sizes.items(), key=lambda item: item[1], reverse=True))
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Directory Sizes</title>
            <link rel="stylesheet" href="./static/style.css" media="all" />
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>Directory Sizes</h1>
            <div class="d_sizes_wp">
                <div class="summary">
                    <p>Total Size: {{ total_size_gb|default(0) | round(2) }} GB</p>
                    <p>Usage: {{ usage_percentage|default(0)  | round(2) }}%</p>
                    <p>Last updated at: {{ last_updated }}</p>
                </div>
                <canvas id="sizeChart" width="400" height="400"></canvas>
                <div class="d_sizes_list">
                    <ul>
                    {% for dir, size in sizes.items() %}
                        <li>{{ dir }}: {{ size }} MB</li>
                    {% endfor %}
                    </ul>
                </div>
            </div>
            <script>
                var ctx = document.getElementById('sizeChart').getContext('2d');
                var sizeChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: {{ sizes.keys() | list | tojson }},
                        datasets: [{
                            label: 'Directory Sizes (MB)',
                            data: {{ sizes.values() | list | tojson }},
                            backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        scales: {
                            x: {
                                beginAtZero: true
                            }
                        }
                    }
                });
            </script>
        </body>
        </html>
    """, sizes=sorted_sizes, total_size_gb=total_size_gb, usage_percentage=usage_percentage, last_updated=app.config.get('LAST_UPDATED', 'Not updated yet'))

@app.route('/api/sizes', methods=['GET'])
def api_sizes():
    sizes = app.config.get('DIRECTORY_SIZES', {})
    return jsonify(sizes)

@app.route('/api/last_updated', methods=['GET'])
def api_last_updated():
    last_updated = app.config.get('LAST_UPDATED', 'Not updated yet')
    return jsonify({'last_updated': last_updated})

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_directory_sizes, 'interval', minutes=3)  # 30分ごとに実行
    update_directory_sizes()  # 初回実行
    scheduler.start()

    try:
        app.run(debug=True)
    finally:
        scheduler.shutdown()
