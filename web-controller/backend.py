import base64
import json

from flask import request, Flask, render_template
from celery.result import AsyncResult
from flask_sqlalchemy import SQLAlchemy
from minio import Minio
from sqlalchemy_utils import create_database, database_exists
import os

from werkzeug.utils import secure_filename

import extract

ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY')
SECRET_KEY = os.environ.get('MINIO_SECRET_KEY')

MINIO_URL = os.environ.get("MINIO_URL")
MINIO_CLIENT = Minio(MINIO_URL, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=False)

url = "postgresql://" + os.environ["POSTGRES_USER"] + ":" + os.environ[
    "POSTGRES_PASSWORD"] + "@" + os.environ["POSTGRES_DB"] + "/jobs"
if not database_exists(url):
    create_database(url)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = url
db = SQLAlchemy(app)


class Task(db.Model):
    __tablename__ = 'result'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(length=100))
    task_type = db.Column(db.String(length=100))


db.create_all()


@app.route('/')
def index():
    return controller()


@app.route('/controller', methods=['GET'])
def controller():
    return render_template('controller.html')


@app.route('/display')
def display():
    return list_gif()


@app.route('/make-bucket', methods=['GET', 'POST'])
def make_bucket():
    bucket_name = request.form['newbucket']
    MINIO_CLIENT.make_bucket(bucket_name)
    # return "Bucket " + bucket_name + " created"
    return render_template('controller.html')


@app.route('/list-buckets', methods=['GET'])
def list_buckets():
    ret = []
    for bucket in MINIO_CLIENT.list_buckets():
        ret.append(bucket.name)
    return json.dumps(list(ret))
    # return render_template('controller.html')


@app.route('/put-video', methods=['GET', 'POST'])
def put_video():
    bucket_name = request.form['bucket']

    if bucket_name == "":
        bucket_name = "videos"

    f = request.files['file']
    f.save(secure_filename(f.filename))
    MINIO_CLIENT.fput_object(bucket_name=bucket_name, object_name=f.filename, file_path=f.filename,
                             content_type=f.content_type)
    os.remove(f.filename)
    return render_template('controller.html')


# submit jobs to the queue
@app.route('/convert', methods=['GET', 'POST'])
def convert():
    video = request.form["video"]
    bucket = request.form["bucket"]

    if bucket == "":
        bucket = "videos"

    if not MINIO_CLIENT.bucket_exists(bucket):
        return "Bucket does not exist"

    task = extract.celery_app.send_task('extract.get_frames', queue='q01', kwargs={'video': video, 'bucket': bucket})
    new = Task(task_id=task.task_id, task_type="extract")
    db.session.add(new)
    try:
        db.session.commit()
    except:
        db.session.rollback()
    # return "Converting"
    return render_template('controller.html')


@app.route('/convert-bucket', methods=['GET', 'POST'])
def convert_all():
    bucket_name = request.form["bucket"]

    if bucket_name == "":
        bucket_name = "videos"

    if not MINIO_CLIENT.bucket_exists(bucket_name):
        return "Bucket does not exist"

    all_vid = MINIO_CLIENT.list_objects(bucket_name=bucket_name)
    for vid in all_vid:
        MINIO_CLIENT.fget_object(bucket_name=bucket_name, object_name=vid.object_name, file_path=vid.object_name)
        task = extract.celery_app.send_task('extract.get_frames', queue='q01',
                                            kwargs={'video': vid.object_name, 'bucket': bucket_name})
        new = Task(task_id=task.task_id, task_type="extract")
        db.session.add(new)
        try:
            db.session.commit()
        except:
            db.session.rollback()
    # return "Converting all videos inside the bucket"
    return render_template('controller.html')


@app.route('/list-gif', methods=['GET'])
def list_gif():
    all_gif = []
    obj_names = []
    for obj in MINIO_CLIENT.list_objects(bucket_name='gif'):
        gif = MINIO_CLIENT.get_object(bucket_name='gif', object_name=obj.object_name)
        all_gif.append(base64.b64encode(gif.read()).decode('utf-8'))
        obj_names.append(obj.object_name)
    return render_template('display.html', all_gif=all_gif, obj_names=obj_names, len=len(obj_names))


@app.route('/track', methods=['GET', 'POST'])
def track():
    eq = []
    cq = []
    for task in Task.query.all():
        res = AsyncResult(task.task_id)
        if (task.task_type == "extract") and (res.state == "SUCCESS") and (res.result not in cq):
            new = Task(task_id=res.result, task_type="compose")
            db.session.add(new)
            try:
                db.session.commit()
            except:
                db.session.rollback()
        if task.task_type == "extract" and res.result not in cq:
            eq.append(task.task_id)
        elif task.task_type == "compose" and task.task_id not in cq:
            cq.append(task.task_id)
    obj = json.dumps({"extract_q": eq, "compose_q": cq})

    tid = request.form["tid"]

    if tid == "":
        return obj

    if tid not in eq and tid not in cq:
        return obj
    else:
        if tid in eq:
            process = "Extract: "
        else:
            process = "Compose: "
        task_result = AsyncResult(tid)
        return process + " " + task_result.state


@app.route('/delete-all', methods=['POST'])
def delete_all():
    for obj in MINIO_CLIENT.list_objects(bucket_name='gif'):
        MINIO_CLIENT.remove_object(bucket_name='gif', object_name=obj.object_name)
    return list_gif()


@app.route('/delete', methods=['POST'])
def delete():
    obj = request.form["delete_obj"]
    MINIO_CLIENT.remove_object(bucket_name='gif', object_name=obj)
    return list_gif()


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=5000)
