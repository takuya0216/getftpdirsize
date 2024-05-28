# getftpdirsize

FTPサーバーの特定のフォルダ内のサブフォルダ容量を取得し、表示するwebアプリ

## Built With

* python 3.10.0
* Flask
* python-dotenv
* apscheduler

## Getting Started

1. install python and libs in requrements.txt.
2. edit .env for your ftp host and account.
FTPPATH is the root path for capacity aggregation.  app aggregates subfolders within the root folder in order.
3. If you want to customize specific path, you can edit update_directory_sizes() in app.py.
```python
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
```
subdir_path is the folder to be aggregated

## Usage

run app.
  ```sh
  python app.py
  ```

wait a few seconds to init app.
this app run at local.
```
* Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5050
 ```

 access http://127.0.0.1:5050 or your setting.

 ## APIs
 #GET
 * /api/sizes<br>
  Returns list of sizes in json format.
 * /api/last_updated<br>
  Returns last update datetime in json format.